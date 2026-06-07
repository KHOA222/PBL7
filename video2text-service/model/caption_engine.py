"""
Caption engine tách từ app_gradio.py.
- Production: bật USE_REAL_MODEL=1 và đặt đủ checkpoints/model_info.json, vocab.pkl, best_model.pt.
- Demo/MVP: nếu thiếu checkpoint hoặc CLIP, tự dùng MockCaptionEngine để hệ thống vẫn chạy được.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from model.base_model import BaseVideoCaptionModel
from utils.video_reader import read_video_stats


class MockCaptionEngine(BaseVideoCaptionModel):
    def generate(self, video_path: str) -> dict:
        t0 = time.time()
        stats = read_video_stats(video_path)
        if not stats["exists"]:
            caption = "Không tìm thấy video để sinh mô tả."
        elif stats["duration"] > 0:
            caption = f"A short video clip with approximately {stats['duration']:.1f} seconds of visual content."
        else:
            caption = "A video clip is uploaded and ready for caption generation."
        return {
            "caption": caption,
            "model_name": "MockCaptionEngine",
            "processing_time": round(time.time() - t0, 3),
            "is_mock": True,
        }


class RealCaptionEngine(BaseVideoCaptionModel):
    """Wrapper quanh CaptionEngine trong app Gradio gốc.

    Để tránh làm MVP bị lỗi vì thiếu GPU/checkpoint, class này chỉ load khi USE_REAL_MODEL=1.
    Bạn có thể copy đầy đủ class CaptionEngine từ app_gradio.py vào đây khi đưa model thật vào production.
    """

    def __init__(self, info_path: str = "checkpoints/model_info.json"):
        try:
            from app_gradio_runtime import CaptionEngine  # optional file nếu muốn copy nguyên bản Gradio engine
        except Exception as exc:
            raise RuntimeError(
                "Chưa có app_gradio_runtime.py. Hãy copy CaptionEngine từ app_gradio.py hoặc dùng MockCaptionEngine."
            ) from exc
        self.engine = CaptionEngine(Path(info_path))

    def generate(self, video_path: str) -> dict:
        t0 = time.time()
        caption, attn_map, elapsed = self.engine.caption(video_path)
        return {
            "caption": caption,
            "model_name": "CLIP_LSTM_Attention",
            "processing_time": round(elapsed or (time.time() - t0), 3),
            "is_mock": False,
        }


def get_caption_engine() -> BaseVideoCaptionModel:
    use_real = os.getenv("USE_REAL_MODEL", "0") == "1"
    info_path = os.getenv("MODEL_INFO_PATH", "checkpoints/model_info.json")
    if use_real:
        try:
            return RealCaptionEngine(info_path=info_path)
        except Exception as exc:
            print(f"[warn] Cannot load real model: {exc}. Fallback to mock engine.")
    return MockCaptionEngine()
