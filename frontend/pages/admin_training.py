import streamlit as st
import requests
import json
from utils import api_url, auth_headers

def admin_training_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem; text-align: left;">🧠 Huấn luyện Mô hình AI (Training)</h1>', unsafe_allow_html=True)
    
    # Form to create new training job
    with st.container(border=True, key="create_training_job_form"):
        st.markdown("<h3>🚀 Khởi tạo phiên Huấn luyện mới</h3>", unsafe_allow_html=True)
        model_name = st.text_input("Tên mô hình (Model Name)", placeholder="Ví dụ: Video-Captioner-ResNet...", key="train_model_name")
        
        # Hyperparameters
        c_lr, c_epochs, c_batch = st.columns(3)
        with c_lr:
            lr = st.number_input("Learning Rate", min_value=0.00001, max_value=0.1, value=0.001, format="%.5f")
        with c_epochs:
            epochs = st.number_input("Epochs", min_value=1, max_value=100, value=5)
        with c_batch:
            batch_size = st.number_input("Batch Size", min_value=1, max_value=256, value=16)
            
        if st.button("Tạo tiến trình Huấn luyện", key="create_job_btn", use_container_width=True):
            if not model_name.strip():
                st.error("Vui lòng nhập tên mô hình!")
            else:
                config = {"learning_rate": lr, "epochs": int(epochs), "batch_size": int(batch_size)}
                try:
                    create_res = requests.post(
                        api_url("/api/admin/training/jobs"),
                        json={"model_name": model_name.strip(), "config_json": json.dumps(config)},
                        headers=auth_headers(),
                        timeout=20
                    )
                    if create_res.ok:
                        st.success("Tạo tiến trình huấn luyện thành công!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi khởi tạo: {create_res.text}")
                except Exception as exc:
                    st.error(f"Lỗi: {exc}")

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

    # List training jobs
    st.markdown("<h3>📋 Nhật ký Huấn luyện (Training Log)</h3>", unsafe_allow_html=True)
    try:
        jobs_res = requests.get(api_url("/api/admin/training/jobs"), headers=auth_headers(), timeout=20)
        jobs = jobs_res.json() if jobs_res.ok else []
    except Exception as exc:
        st.error(f"Lỗi tải danh sách tiến trình: {exc}")
        jobs = []

    if not jobs:
        st.info("Chưa có tiến trình huấn luyện nào.")
        return

    # Render jobs
    for j in reversed(jobs):
        with st.container(border=True, key=f"job_item_{j['id']}"):
            c_info, c_action = st.columns([3, 1])
            with c_info:
                status_color = "#3b82f6" if j["status"] == "pending" else (
                    "#f59e0b" if j["status"] == "running" else (
                        "#a855f7" if j["status"] == "evaluating" else (
                            "#10b981" if j["status"] == "completed" else "#ef4444"
                        )
                    )
                )
                
                st.markdown(f"""
                <div>
                    <h4 style="margin: 0; font-size: 1.15rem; color: var(--text-primary);">{j['model_name']} (Job #{j['id']})</h4>
                    <div style="margin: 0.4rem 0;">
                        Trạng thái: <span style="color: {status_color}; font-weight: 700; text-transform: uppercase;">{j['status']}</span>
                        | Dataset Size: <b>{j['dataset_size']}</b>
                        | Ngày tạo: {j['created_at'][:16].replace('T', ' ')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Show config
                if j.get("config_json"):
                    cfg = json.loads(j["config_json"])
                    st.markdown(f"⚙️ Config: `LR: {cfg.get('learning_rate')}`, `Epochs: {cfg.get('epochs')}`, `Batch: {cfg.get('batch_size')}`")
                    
                # Show metrics if completed
                if j["status"] == "completed" and j.get("result_metrics_json"):
                    metrics = json.loads(j["result_metrics_json"])
                    st.markdown(f"🏆 Kết quả đánh giá: `BLEU-4: {metrics.get('bleu_4', 0):.4f}`, `CIDEr: {metrics.get('cider', 0):.4f}`, `Loss: {metrics.get('loss', 0):.4f}`")
                    
            with c_action:
                if j["status"] == "pending":
                    if st.button("▶️ Bắt đầu Train", key=f"start_job_{j['id']}", use_container_width=True):
                        try:
                            start_res = requests.post(
                                api_url(f"/api/admin/training/jobs/{j['id']}/start"),
                                headers=auth_headers(),
                                timeout=20
                            )
                            if start_res.ok:
                                st.success("Đã kích hoạt tiến trình huấn luyện thành công!")
                                st.rerun()
                            else:
                                st.error(start_res.text)
                        except Exception as exc:
                            st.error(f"Lỗi: {exc}")
                elif j["status"] in ["running", "evaluating"]:
                    st.markdown("<div style='text-align: center; color: #f59e0b; font-weight: 600; padding-top: 1rem;'>⌛ Đang thực thi...</div>", unsafe_allow_html=True)
                    if st.button("🔄 Tải lại", key=f"reload_job_{j['id']}", use_container_width=True):
                        st.rerun()
                elif j["status"] == "completed":
                    st.markdown("<div style='text-align: center; color: #10b981; font-weight: 600; padding-top: 1rem;'>✅ Đã hoàn thành</div>", unsafe_allow_html=True)
                elif j["status"] == "failed":
                    st.markdown("<div style='text-align: center; color: #ef4444; font-weight: 600; padding-top: 1rem;'>❌ Đã thất bại</div>", unsafe_allow_html=True)
