import streamlit as st
import requests
from utils import api_url, auth_headers

def upload_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem;">Tải lên Video mới</h1>', unsafe_allow_html=True)
    
    if not st.session_state.token:
        col2 = st.container()
        with col2:
            st.warning("⚠️ Bạn cần đăng nhập trước khi tải video lên.")
            if st.button("Đăng nhập ngay", use_container_width=True):
                st.session_state.page = "Login"
                st.rerun()
    else:
        col2 = st.container()
        with col2:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <p style="color: var(--text-muted); font-size: 1.05rem;">Chia sẻ những khoảnh khắc tuyệt vời của bạn với mọi người và sử dụng AI để dịch thuật & sinh phụ đề tự động.</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.container(border=True, key="upload_form"):
                st.markdown("<h3 style='margin-top: 0; margin-bottom: 1.2rem; text-align: center;'>📤 THÔNG TIN CHI TIẾT</h3>", unsafe_allow_html=True)
                title = st.text_input("Tiêu đề video", placeholder="Nhập tiêu đề hấp dẫn cho video...")
                description = st.text_area("Mô tả chi tiết", placeholder="Chia sẻ thêm thông tin về video này...")
                hashtags = st.text_input("Hashtag liên quan", placeholder="Ví dụ: #ai #technology #nature")
                
                st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
                file = st.file_uploader("Chọn tệp video", type=["mp4", "mov", "avi", "webm"])
                
                st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
                if st.button("🚀 Bắt đầu tải lên", use_container_width=True):
                    if not title.strip():
                        st.error("Vui lòng nhập tiêu đề cho video!")
                    elif not file:
                        st.error("Vui lòng chọn một tệp video!")
                    else:
                        files = {"file": (file.name, file.getvalue(), file.type or "video/mp4")}
                        data = {"title": title, "description": description, "hashtags": hashtags}
                        try:
                            with st.spinner("Đang truyền tệp tin lên hệ thống..."):
                                res = requests.post(
                                    api_url("/api/videos/upload"),
                                    data=data,
                                    files=files,
                                    headers=auth_headers(),
                                    timeout=180,
                                )
                                if res.ok:
                                    st.success("🎉 Tải lên video thành công!")
                                    st.session_state.page = "Home Feed"
                                    st.rerun()
                                else:
                                    st.error(f"Tải lên thất bại: {res.text}")
                        except Exception as exc:
                            st.error(f"Lỗi kết nối upload: {exc}")
