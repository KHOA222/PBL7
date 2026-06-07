import streamlit as st
import requests
from utils import api_url, auth_headers, get_username

def admin_caption_review_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem; text-align: left;">✍️ Duyệt Phụ đề AI</h1>', unsafe_allow_html=True)
    
    # Filter selection
    filter_status = st.selectbox("Lọc theo trạng thái", ["pending", "approved", "rejected"], index=0, key="caption_filter_sel")
    
    try:
        res = requests.get(api_url(f"/api/admin/caption-reviews?status={filter_status}"), headers=auth_headers(), timeout=20)
        reviews = res.json() if res.ok else []
    except Exception as exc:
        st.error(f"Không tải được danh sách kiểm duyệt: {exc}")
        reviews = []

    if not reviews:
        st.info(f"Không có yêu cầu kiểm duyệt phụ đề nào ở trạng thái '{filter_status}'.")
        return

    # List reviews
    for r in reviews:
        with st.container(border=True, key=f"review_card_{r['id']}"):
            st.markdown(f"<h4>Yêu cầu #{r['id']} (Video ID: {r['video_id']})</h4>", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background: rgba(139, 92, 246, 0.05); padding: 0.8rem 1.2rem; border-radius: 10px; margin-bottom: 0.8rem; border-left: 4px solid #8b5cf6;">
                <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">🤖 AI Caption gốc:</div>
                <div style="color: var(--text-primary); font-size: 0.95rem; line-height: 1.4; font-style: italic;">"{r['ai_caption']}"</div>
            </div>
            """, unsafe_allow_html=True)
            
            if r.get("corrected_caption"):
                st.markdown(f"""
                <div style="background: rgba(16, 185, 129, 0.05); padding: 0.8rem 1.2rem; border-radius: 10px; margin-bottom: 0.8rem; border-left: 4px solid #10b981;">
                    <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">✍️ Phụ đề đã sửa đổi:</div>
                    <div style="color: var(--text-primary); font-size: 0.95rem; line-height: 1.4;">"{r['corrected_caption']}"</div>
                </div>
                """, unsafe_allow_html=True)

            if filter_status == "pending":
                # Edit input form
                corrected_input = st.text_input(
                    "Sửa đổi phụ đề (để trống nếu duyệt bản dịch gốc)",
                    value=r.get("corrected_caption") or r["ai_caption"],
                    key=f"edit_inp_{r['id']}"
                )
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    # Approve original
                    if st.button("✅ Chấp thuận bản gốc", key=f"app_orig_{r['id']}", use_container_width=True):
                        try:
                            app_res = requests.post(
                                api_url(f"/api/admin/caption-reviews/{r['id']}/approve"),
                                headers=auth_headers(),
                                timeout=20
                            )
                            if app_res.ok:
                                st.success("Đã duyệt thành công!")
                                st.rerun()
                            else:
                                st.error(app_res.text)
                        except Exception as exc:
                            st.error(f"Lỗi: {exc}")
                with c2:
                    # Edit & approve
                    if st.button("✏️ Cập nhật & Duyệt", key=f"app_edit_{r['id']}", use_container_width=True):
                        if not corrected_input.strip():
                            st.error("Nội dung phụ đề chỉnh sửa không được để trống!")
                        else:
                            try:
                                edit_res = requests.post(
                                    api_url(f"/api/admin/caption-reviews/{r['id']}/edit"),
                                    json={"corrected_caption": corrected_input.strip()},
                                    headers=auth_headers(),
                                    timeout=20
                                )
                                if edit_res.ok:
                                    st.success("Đã cập nhật phụ đề và duyệt thành công!")
                                    st.rerun()
                                else:
                                    st.error(edit_res.text)
                            except Exception as exc:
                                st.error(f"Lỗi: {exc}")
                with c3:
                    # Reject
                    if st.button("❌ Từ chối / Loại bỏ", key=f"app_rej_{r['id']}", use_container_width=True):
                        try:
                            rej_res = requests.post(
                                api_url(f"/api/admin/caption-reviews/{r['id']}/reject"),
                                headers=auth_headers(),
                                timeout=20
                            )
                            if rej_res.ok:
                                st.warning("Đã từ chối phụ đề!")
                                st.rerun()
                            else:
                                st.error(rej_res.text)
                        except Exception as exc:
                            st.error(f"Lỗi: {exc}")
            else:
                # Show review info for non-pending
                reviewer = get_username(r.get("reviewed_by")) if r.get("reviewed_by") else "N/A"
                reviewed_date = r.get("reviewed_at")[:16].replace("T", " ") if r.get("reviewed_at") else "N/A"
                st.markdown(f"""
                <div style="font-size: 0.85rem; color: var(--text-muted); font-style: italic;">
                    Người duyệt: {reviewer} | Thời gian: {reviewed_date}
                </div>
                """, unsafe_allow_html=True)
