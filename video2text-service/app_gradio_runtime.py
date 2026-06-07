"""
app_gradio.py
=============
Gradio web app cho MSRVTT Video Captioning.
Load model từ model_info.json — không cần import training code.

Cài đặt:
    pip install gradio>=4.0 opencv-python Pillow torch
    pip install git+https://github.com/openai/CLIP.git

Chạy:
    python app_gradio.py
    python app_gradio.py --info checkpoints/model_info.json
    python app_gradio.py --share          # tạo public link (Gradio tunnel)
    python app_gradio.py --port 7861      # đổi port
"""

import argparse
import gc
import json
import pickle
import sys
import tempfile
import time
from pathlib import Path
import socket

import cv2
import gradio as gr
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

import clip

# ══════════════════════════════════════════════════════════════════
#  ĐỌC CONFIG TỪ model_info.json
# ══════════════════════════════════════════════════════════════════

DEFAULT_INFO = Path("checkpoints/model_info.json")


def load_config(info_path: Path) -> dict:
    if not info_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {info_path}\n"
            "Hãy train xong rồi chạy save_model_info.py trước."
        )
    with open(info_path, encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════════════════════
#  MODEL DEFINITION (copy từ model_lstm_attention.py)
#  Tách ra để app không phụ thuộc vào file training
# ══════════════════════════════════════════════════════════════════

class VideoEncoder(nn.Module):
    def __init__(self, clip_dim, video_dim, hidden_dim, dropout):
        super().__init__()
        self.proj   = nn.Sequential(
            nn.Linear(clip_dim, video_dim),
            nn.LayerNorm(video_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
        )
        self.init_h = nn.Linear(video_dim, hidden_dim)
        self.init_c = nn.Linear(video_dim, hidden_dim)

    def forward(self, x):
        enc = self.proj(x)
        m   = enc.mean(1)
        h0  = torch.tanh(self.init_h(m)).unsqueeze(0)
        c0  = torch.tanh(self.init_c(m)).unsqueeze(0)
        return enc, h0, c0


class BahdanauAttention(nn.Module):
    def __init__(self, video_dim, hidden_dim, attn_dim):
        super().__init__()
        self.W_enc = nn.Linear(video_dim,  attn_dim, bias=False)
        self.W_dec = nn.Linear(hidden_dim, attn_dim, bias=False)
        self.v     = nn.Linear(attn_dim, 1, bias=False)

    def forward(self, enc, h):
        e     = self.v(torch.tanh(
            self.W_enc(enc) + self.W_dec(h).unsqueeze(1)
        )).squeeze(-1)
        alpha   = F.softmax(e, -1)
        context = (alpha.unsqueeze(-1) * enc).sum(1)
        return context, alpha


class LSTMDecoder(nn.Module):
    def __init__(self, vocab_size, embed_dim, video_dim, hidden_dim,
                 attn_dim, dropout, pad_idx, bos_idx, eos_idx, max_gen_len):
        super().__init__()
        self.bos_idx    = bos_idx
        self.eos_idx    = eos_idx
        self.max_gen_len= max_gen_len
        self.embed  = nn.Embedding(vocab_size, embed_dim, padding_idx=pad_idx)
        self.attn   = BahdanauAttention(video_dim, hidden_dim, attn_dim)
        self.cell   = nn.LSTMCell(embed_dim + video_dim, hidden_dim)
        self.fc_out = nn.Linear(hidden_dim + video_dim, vocab_size)
        self.drop   = nn.Dropout(dropout)

    def step(self, token, enc, h, c):
        emb    = self.drop(self.embed(token))
        ctx, a = self.attn(enc, h)
        h, c   = self.cell(torch.cat([emb, ctx], -1), (h, c))
        h      = self.drop(h)
        logit  = self.fc_out(torch.cat([h, ctx], -1))
        return logit, h, c, a

    @torch.no_grad()
    def beam_search(self, enc, h0, c0, beam=5, lp=0.7):
        device  = enc.device
        enc_exp = enc.expand(beam, -1, -1).contiguous()
        h = h0.squeeze(0).expand(beam, -1).contiguous()
        c = c0.squeeze(0).expand(beam, -1).contiguous()
        seqs   = torch.full((beam, 1), self.bos_idx, dtype=torch.long, device=device)
        scores = torch.zeros(beam, device=device)
        done   = []

        for step in range(self.max_gen_len):
            logit, h, c, _ = self.step(seqs[:, -1], enc_exp, h, c)
            log_probs = F.log_softmax(logit, dim=-1)
            total = scores.unsqueeze(1) + log_probs
            top_scores, top_idx = total.view(-1).topk(beam * 2)
            beam_ids  = top_idx // logit.size(-1)
            token_ids = top_idx %  logit.size(-1)
            new_seqs, new_h, new_c, new_scores = [], [], [], []
            for i in range(len(top_scores)):
                bi, tid = beam_ids[i].item(), token_ids[i].item()
                new_seq = torch.cat([seqs[bi], token_ids[i:i+1]])
                if tid == self.eos_idx or step == self.max_gen_len - 1:
                    lp_s = ((5 + new_seq.size(0)) / 6) ** lp
                    done.append((top_scores[i].item() / lp_s, new_seq))
                else:
                    new_seqs.append(new_seq); new_h.append(h[bi])
                    new_c.append(c[bi]); new_scores.append(top_scores[i].item())
                if len(new_seqs) == beam:
                    break
            if not new_seqs:
                break
            max_l  = max(s.size(0) for s in new_seqs)
            padded = torch.zeros(len(new_seqs), max_l, dtype=torch.long, device=device)
            for i, s in enumerate(new_seqs):
                padded[i, :s.size(0)] = s
            seqs   = padded
            h      = torch.stack(new_h)
            c      = torch.stack(new_c)
            scores = torch.tensor(new_scores, device=device)

        if not done:
            done = [(scores[i].item(), seqs[i]) for i in range(len(seqs))]
        best = max(done, key=lambda x: x[0])[1].tolist()
        toks = best[1:]
        if self.eos_idx in toks:
            toks = toks[:toks.index(self.eos_idx)]
        return toks if toks else [self.bos_idx]  # guard empty

    @torch.no_grad()
    def sample_decode(self, enc, h0, c0, top_k=50, temperature=1.0):
        device = enc.device
        h = h0.squeeze(0)
        c = c0.squeeze(0)
        token = torch.tensor([self.bos_idx], dtype=torch.long, device=device)
        seq = []
        temp = max(float(temperature), 1e-4)
        k = int(top_k)

        for _ in range(self.max_gen_len):
            logit, h, c, _ = self.step(token, enc, h, c)
            logits = logit.squeeze(0) / temp
            if k > 0 and k < logits.numel():
                top_vals, top_idx = torch.topk(logits, k)
                probs = F.softmax(top_vals, dim=-1)
                next_id = top_idx[torch.multinomial(probs, 1)]
            else:
                probs = F.softmax(logits, dim=-1)
                next_id = torch.multinomial(probs, 1)
            tid = int(next_id.item())
            if tid == self.eos_idx:
                break
            seq.append(tid)
            token = next_id.view(1)

        return seq if seq else [self.bos_idx]


class VideoCaptionModel(nn.Module):
    def __init__(self, cfg: dict, vocab_size: int):
        super().__init__()
        a = cfg["model_arch"]
        v = cfg["vocab"]
        self.encoder = VideoEncoder(a["clip_dim"], a["video_dim"],
                                    a["hidden_dim"], a["dropout"])
        self.decoder = LSTMDecoder(
            vocab_size   = vocab_size,
            embed_dim    = a["embed_dim"],
            video_dim    = a["video_dim"],
            hidden_dim   = a["hidden_dim"],
            attn_dim     = a["attn_dim"],
            dropout      = a["dropout"],
            pad_idx      = v["pad_idx"],
            bos_idx      = v["bos_idx"],
            eos_idx      = v["eos_idx"],
            max_gen_len  = a["max_gen_len"],
        )

    @torch.no_grad()
    def generate(self, video_feat, beam=5):
        self.eval()
        enc, h0, c0 = self.encoder(video_feat)
        results = []
        for i in range(enc.size(0)):
            toks = self.decoder.beam_search(
                enc[i:i+1], h0[:, i:i+1], c0[:, i:i+1], beam
            )
            results.append(toks)
        return results


# ══════════════════════════════════════════════════════════════════
#  INFERENCE ENGINE (singleton — load 1 lần, dùng mãi)
# ══════════════════════════════════════════════════════════════════

class CaptionEngine:
    """Thread-safe singleton. Load model + CLIP vào VRAM một lần duy nhất."""

    def __init__(self, info_path: Path):
        self.cfg      = load_config(info_path)
        self.device   = "cuda" if torch.cuda.is_available() else "cpu"
        self.amp      = self.cfg["training"]["amp_enabled"] and self.device == "cuda"
        self._load_vocab()
        self._load_model()
        self._load_clip()
        print(f"\n✅ Engine ready  |  device={self.device}  |  vocab={self.vocab_size:,}")

    def _load_vocab(self):
        vocab_path = Path(self.cfg["vocab"]["vocab_pkl"])
        if not vocab_path.exists():
            fallback_path = Path(__file__).parent / "checkpoints" / "vocab.pkl"
            if fallback_path.exists():
                vocab_path = fallback_path
            else:
                raise FileNotFoundError(f"vocab.pkl không tìm thấy tại: {vocab_path} hoặc {fallback_path}")
        with open(vocab_path, "rb") as f:
            vocab = pickle.load(f)
        self.idx2word   = vocab["idx2word"]
        self.vocab_size = vocab["vocab_size"]

    def _load_model(self):
        ckpt_path = Path(self.cfg["inference_paths"]["checkpoint"])
        if not ckpt_path.exists():
            fallback_path = Path(__file__).parent / "checkpoints" / "best_model.pt"
            if fallback_path.exists():
                ckpt_path = fallback_path
            else:
                raise FileNotFoundError(f"Checkpoint không tìm thấy tại: {ckpt_path} hoặc {fallback_path}")
        self.model = VideoCaptionModel(self.cfg, self.vocab_size).to(self.device)
        ckpt = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["model"])
        self.model.eval()
        n_params = sum(p.numel() for p in self.model.parameters())
        print(f"   Model params : {n_params:,}  |  epoch={ckpt.get('epoch','?')}")

    def _load_clip(self):
        clip_name = self.cfg["model_arch"]["clip_model"]
        self.clip_model, self.preprocess = clip.load(clip_name, device=self.device)
        self.clip_model.eval()
        print(f"   CLIP         : {clip_name}")

    def _sample_frames(self, video_path: str, n: int):
        cap   = cv2.VideoCapture(video_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            cap.release()
            return []
        indices = np.unique(np.linspace(0, total - 1, n, dtype=int))
        frames  = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret:
                frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        cap.release()
        return frames

    def _extract_features(self, frames):
        n_frames = self.cfg["model_arch"]["n_frames"]
        tensors  = [self.preprocess(f) for f in frames]
        all_feat = []
        for i in range(0, len(tensors), 64):
            batch = torch.stack(tensors[i:i+64]).to(self.device)
            with torch.no_grad(), torch.amp.autocast("cuda", enabled=self.amp):
                feats = self.clip_model.encode_image(batch).float().cpu().numpy()
            all_feat.append(feats)
        feats = np.concatenate(all_feat, axis=0).astype(np.float32)
        # Pad nếu thiếu frame
        if feats.shape[0] < n_frames:
            pad   = np.zeros((n_frames - feats.shape[0], feats.shape[1]), dtype=np.float32)
            feats = np.concatenate([feats, pad], axis=0)
        return feats[:n_frames]

    def _decode(self, token_ids):
        words = [
            self.idx2word[tid] for tid in token_ids
            if self.idx2word.get(tid) not in (None, "<PAD>", "<BOS>", "<EOS>", "<UNK>")
        ]
        return " ".join(words)

    def caption(
        self,
        video_path: str,
        beam_size: int = 5,
        length_penalty: float = 0.7,
        decode_mode: str = "beam",
        top_k: int = 50,
        temperature: float = 1.0,
    ) -> tuple[str, list, float]:
        """
        Returns:
            caption   (str)    — caption text
            attn_map  (list)   — attention per frame (list of floats) — dùng để visualize
            elapsed   (float)  — inference time (s)
        """
        t0     = time.time()
        frames = self._sample_frames(video_path, self.cfg["model_arch"]["n_frames"])
        if not frames:
            raise ValueError("Không đọc được frame từ video — kiểm tra định dạng file.")

        feats      = self._extract_features(frames)
        video_feat = torch.from_numpy(feats).unsqueeze(0).to(self.device)

        with torch.no_grad(), torch.amp.autocast("cuda", enabled=self.amp):
            # Lấy attention weights từ step cuối cùng để visualize
            enc, h0, c0 = self.model.encoder(video_feat)
            if decode_mode == "sample":
                toks = self.model.decoder.sample_decode(
                    enc[0:1], h0[:, 0:1], c0[:, 0:1], top_k=top_k, temperature=temperature
                )
            else:
                toks = self.model.decoder.beam_search(
                    enc[0:1], h0[:, 0:1], c0[:, 0:1], beam=beam_size, lp=length_penalty
                )
            # Lấy attention weights bằng cách forward lại token đầu
            _, alpha = self.model.decoder.attn(enc[0:1], h0[0])
            attn_map = alpha[0].cpu().float().tolist()

        caption = self._decode(toks)
        elapsed = time.time() - t0
        return caption, attn_map, elapsed

    def get_model_info_text(self) -> str:
        c   = self.cfg
        ma  = c["model_arch"]
        sc  = c.get("best_scores", {})
        tr  = c["training"]
        lines = [
            f"**Checkpoint**: epoch {c['best_epoch']}  —  {c['created_at']}",
            f"**CLIP**: {ma['clip_model']}  |  **Frames/video**: {ma['n_frames']}",
            f"**Hidden**: {ma['hidden_dim']}  |  **Embed**: {ma['embed_dim']}  |  **Attn**: {ma['attn_dim']}",
            f"**Dropout**: {ma['dropout']}  |  **Beam size**: {ma['beam_size']}",
            "",
            "**Val metrics (best epoch)**",
            f"CIDEr: `{sc.get('CIDEr','—')}`  BLEU-4: `{sc.get('BLEU-4','—')}`  "
            f"METEOR: `{sc.get('METEOR','—')}`  ROUGE-L: `{sc.get('ROUGE-L','—')}`",
            "",
            f"**Training**: LR={tr['lr']}  bs={tr['batch_size']}  AMP={tr['amp_enabled']}  "
            f"time={tr['training_time_min']} phút",
        ]
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
#  ATTENTION RENDERING
# ══════════════════════════════════════════════════════════════════

def render_attention_image(attn: list, n_frames: int) -> np.ndarray:
    """Vẽ attention heatmap theo từng frame (matplotlib → numpy)."""
    # Chuẩn hóa chiều dài và giá trị attention để luôn render được
    if not attn:
        attn = [0.0] * n_frames
    if len(attn) < n_frames:
        attn = attn + [0.0] * (n_frames - len(attn))
    attn = np.array(attn[:n_frames], dtype=np.float32)
    max_val = float(attn.max()) if attn.size else 0.0
    if max_val <= 0:
        max_val = 1.0
    attn = attn / max_val

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 1.2))
        data = attn.reshape(1, -1)
        im   = ax.imshow(data, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
        ax.set_xticks(range(n_frames))
        ax.set_xticklabels([f"f{i+1}" for i in range(n_frames)], fontsize=9)
        ax.set_yticks([])
        ax.set_title("Attention weight per frame", fontsize=10, pad=4)
        plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
        fig.tight_layout(pad=0.5)
        fig.canvas.draw()
        if hasattr(fig.canvas, "tostring_rgb"):
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        else:
            img = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
        plt.close(fig)
        return img
    except Exception as exc:
        # Fallback: tạo heatmap đơn giản bằng numpy nếu matplotlib không có
        h, w = 36, max(200, n_frames * 20)
        bar = (attn * 255).astype(np.uint8)
        bar = np.repeat(bar, w // n_frames + 1)[:w]
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:, :, 0] = 255  # base red channel
        img[:, :, 1] = 255 - bar
        img[:, :, 2] = 255 - bar
        # In lỗi ra console để dễ debug
        print(f"[warn] Attention render fallback: {exc}")
        return img


# ══════════════════════════════════════════════════════════════════
#  APP THEME/CSS
# ══════════════════════════════════════════════════════════════════

APP_THEME = gr.themes.Soft(primary_hue="violet")
APP_CSS = """
#caption-out textarea { font-size: 18px !important; font-weight: 500; }
#attn-img { border-radius: 8px; overflow: hidden; }
footer { display: none !important; }
"""


# ══════════════════════════════════════════════════════════════════
#  BUILD GRADIO UI
# ══════════════════════════════════════════════════════════════════

def build_app(engine: CaptionEngine) -> gr.Blocks:

    def predict(video_file, beam_size, length_penalty, decode_mode, top_k, temperature):
        """Hàm chính — Gradio gọi mỗi khi user submit."""
        if video_file is None:
            return "⚠️ Hãy upload video trước.", None, ""

        try:
            caption, attn_map, elapsed = engine.caption(
                video_file,
                beam_size=int(beam_size),
                length_penalty=float(length_penalty),
                decode_mode=str(decode_mode),
                top_k=int(top_k),
                temperature=float(temperature),
            )
        except Exception as e:
            return f"❌ Lỗi: {e}", None, ""

        # Render attention map thành ảnh thanh màu
        attn_img = render_attention_image(attn_map, engine.cfg["model_arch"]["n_frames"])

        info = (
            f"⏱ {elapsed:.2f}s  |  mode={decode_mode}  |  beam={beam_size}  |  "
            f"lp={length_penalty}  |  top_k={top_k}  |  temp={temperature}  |  "
            f"{len(caption.split())} words"
        )
        return caption, attn_img, info

    with gr.Blocks(
        title="MSRVTT Video Captioning",
    ) as demo:

        gr.Markdown("# 🎬 MSRVTT Video Captioning\nLSTM + Bahdanau Attention · CLIP features")

        with gr.Row():
            # ── Left column: input ─────────────────────────────────
            with gr.Column(scale=1):
                video_input = gr.Video(
                    label="Upload video (.mp4, .avi, .mov, .webm)",
                    height=320,
                )
                decode_radio = gr.Radio(
                    choices=["beam", "sample"],
                    value="beam",
                    label="Decoding mode",
                )
                beam_slider = gr.Slider(
                    minimum=1, maximum=10, value=5, step=1,
                    label="Beam size",
                    info="Cao hơn = chính xác hơn nhưng chậm hơn"
                )
                lp_slider = gr.Slider(
                    minimum=0.2, maximum=1.2, value=0.7, step=0.05,
                    label="Length penalty",
                    info="Thấp hơn = caption dài hơn (thường)"
                )
                topk_slider = gr.Slider(
                    minimum=0, maximum=200, value=50, step=5,
                    label="Top-k (sampling)",
                    info="0 = dùng toàn bộ vocab"
                )
                temp_slider = gr.Slider(
                    minimum=0.3, maximum=1.5, value=1.0, step=0.05,
                    label="Temperature (sampling)",
                )
                submit_btn = gr.Button("▶ Generate Caption", variant="primary", size="lg")

            # ── Right column: output ───────────────────────────────
            with gr.Column(scale=1):
                caption_out = gr.Textbox(
                    label="Generated caption",
                    lines=3,
                    interactive=False,
                    elem_id="caption-out",
                    placeholder="Caption sẽ hiện ở đây sau khi generate...",
                )
                attn_out = gr.Image(
                    label="Attention per frame",
                    elem_id="attn-img",
                    height=130,
                )
                info_out = gr.Markdown("")

        # ── Model info tab ─────────────────────────────────────────
        with gr.Accordion("ℹ️ Model info", open=False):
            gr.Markdown(engine.get_model_info_text())

        # ── Examples ──────────────────────────────────────────────
        gr.Examples(
            examples=[],          # thêm đường dẫn video mẫu nếu có
            inputs=[video_input],
            label="Video mẫu",
        )

        # ── Events ────────────────────────────────────────────────
        submit_btn.click(
            fn      = predict,
            inputs  = [video_input, beam_slider, lp_slider, decode_radio, topk_slider, temp_slider],
            outputs = [caption_out, attn_out, info_out],
        )
        # Tự generate khi upload xong
        video_input.change(
            fn      = predict,
            inputs  = [video_input, beam_slider, lp_slider, decode_radio, topk_slider, temp_slider],
            outputs = [caption_out, attn_out, info_out],
        )
        # Tự generate khi đổi beam size
        beam_slider.change(
            fn      = predict,
            inputs  = [video_input, beam_slider, lp_slider, decode_radio, topk_slider, temp_slider],
            outputs = [caption_out, attn_out, info_out],
        )
        # Tự generate khi đổi length penalty
        lp_slider.change(
            fn      = predict,
            inputs  = [video_input, beam_slider, lp_slider, decode_radio, topk_slider, temp_slider],
            outputs = [caption_out, attn_out, info_out],
        )
        # Tự generate khi đổi decoding mode
        decode_radio.change(
            fn      = predict,
            inputs  = [video_input, beam_slider, lp_slider, decode_radio, topk_slider, temp_slider],
            outputs = [caption_out, attn_out, info_out],
        )
        # Tự generate khi đổi sampling params
        topk_slider.change(
            fn      = predict,
            inputs  = [video_input, beam_slider, lp_slider, decode_radio, topk_slider, temp_slider],
            outputs = [caption_out, attn_out, info_out],
        )
        temp_slider.change(
            fn      = predict,
            inputs  = [video_input, beam_slider, lp_slider, decode_radio, topk_slider, temp_slider],
            outputs = [caption_out, attn_out, info_out],
        )

    return demo


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def _pick_free_port(host: str, start_port: int, max_tries: int = 10) -> int:
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError(
        f"Cannot find empty port in range: {start_port}-{start_port + max_tries - 1}."
    )


def main():
    parser = argparse.ArgumentParser(description="MSRVTT Gradio App")
    parser.add_argument("--info",   default=str(DEFAULT_INFO),
                        help=f"Đường dẫn model_info.json (mặc định: {DEFAULT_INFO})")
    parser.add_argument("--port",   type=int, default=7860,
                        help="Port (mặc định: 7860)")
    parser.add_argument("--share",  action="store_true",
                        help="Tạo public Gradio link")
    parser.add_argument("--host",   default="127.0.0.1",
                        help="Host (mặc định: 127.0.0.1)")
    args = parser.parse_args()

    print("=" * 60)
    print(" MSRVTT Gradio App")
    print("=" * 60)

    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"GPU  : {gpu}  ({vram:.1f} GB VRAM)")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.benchmark        = True
    else:
        print("GPU  : không có — chạy trên CPU")

    engine = CaptionEngine(Path(args.info))
    app    = build_app(engine)

    port = _pick_free_port(args.host, args.port, max_tries=10)
    if port != args.port:
        print(f"⚠️ Port {args.port} đang bận — đổi sang {port}")

    print(f"\n🚀 Khởi động tại http://{args.host}:{port}")
    app.launch(
        server_name = args.host,
        server_port = port,
        share       = args.share,
        inbrowser   = True,
        theme       = APP_THEME,
        css         = APP_CSS,
    )


if __name__ == "__main__":
    main()
