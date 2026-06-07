import streamlit as st
import requests
import json
from utils import api_url, auth_headers

def admin_model_evaluation_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem; text-align: left;">🤖 Đánh giá & Phát triển Mô hình (Model Versions)</h1>', unsafe_allow_html=True)
    
    try:
        res = requests.get(api_url("/api/admin/model-versions"), headers=auth_headers(), timeout=20)
        versions = res.json() if res.ok else []
    except Exception as exc:
        st.error(f"Không tải được danh sách phiên bản mô hình: {exc}")
        versions = []

    if not versions:
        st.info("Chưa có phiên bản mô hình nào. Vui lòng tạo và hoàn thành tiến trình huấn luyện trước.")
        return

    # List model versions in a comparison layout
    st.markdown("<h3>📋 Các phiên bản Mô hình</h3>", unsafe_allow_html=True)
    
    for v in versions:
        with st.container(border=True, key=f"mv_card_{v['id']}"):
            c_info, c_action = st.columns([3, 1])
            with c_info:
                badge_style = "background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid #10b981;" if v["status"] == "current" else (
                    "background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid #3b82f6;" if v["status"] == "candidate" else (
                        "background: rgba(100, 116, 139, 0.1); color: #64748b; border: 1px solid #64748b;"
                    )
                )
                
                st.markdown(f"""
                <div>
                    <h4 style="margin: 0; font-size: 1.2rem; color: var(--text-primary); display: flex; align-items: center; gap: 0.8rem;">
                        Phiên bản: {v['version']}
                        <span style="font-size: 0.75rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 20px; text-transform: uppercase; {badge_style}">
                            {v['status']}
                        </span>
                    </h4>
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin: 0.4rem 0;">
                        Đường dẫn: <code>{v['checkpoint_path']}</code>
                        {f" | Ngày triển khai: {v['deployed_at'][:16].replace('T', ' ')}" if v.get("deployed_at") else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Metrics
                if v.get("metrics_json"):
                    metrics = json.loads(v["metrics_json"])
                    st.markdown(f"📊 Chỉ số: `BLEU-4: {metrics.get('bleu_4', 0):.4f}`, `CIDEr: {metrics.get('cider', 0):.4f}`, `Loss: {metrics.get('loss', 0):.4f}`")
                    
            with c_action:
                if v["status"] == "candidate":
                    if st.button("🚀 Deploy ngay", key=f"deploy_mv_{v['id']}", use_container_width=True):
                        with st.spinner("Đang triển khai mô hình..."):
                            try:
                                dep_res = requests.post(
                                    api_url(f"/api/admin/model-versions/{v['id']}/deploy"),
                                    headers=auth_headers(),
                                    timeout=20
                                )
                                if dep_res.ok:
                                    st.success(f"Triển khai phiên bản {v['version']} thành công!")
                                    st.rerun()
                                else:
                                    st.error(dep_res.text)
                            except Exception as exc:
                                st.error(f"Lỗi: {exc}")
                elif v["status"] == "current":
                    st.markdown("<div style='text-align: center; color: #10b981; font-weight: 700; padding-top: 1rem;'>🟢 Đang chạy (Active)</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='text-align: center; color: #64748b; font-weight: 600; padding-top: 1rem;'>📦 Lưu trữ (Archived)</div>", unsafe_allow_html=True)
