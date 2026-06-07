import streamlit as st
import requests
import html
from utils import api_url, auth_headers, get_username, format_datetime

def video_detail_page():
    if "selected_video_id" not in st.session_state or not st.session_state.selected_video_id:
        st.warning("Không tìm thấy video được yêu cầu.")
        if st.button("Quay lại Trang chủ", use_container_width=True):
            st.session_state.page = "Home Feed"
            st.rerun()
        return

    vid = st.session_state.selected_video_id
    
    # Back button
    if st.button("⬅️ Quay lại bảng tin", key="back_to_feed"):
        st.session_state.page = "Home Feed"
        st.session_state.selected_video_id = None
        st.rerun()

    # Query video details
    try:
        res = requests.get(api_url(f"/api/videos/{vid}"), timeout=20)
        video = res.json() if res.ok else None
    except Exception as exc:
        st.error(f"Lỗi tải thông tin video: {exc}")
        video = None

    if not video:
        st.error("Không tìm thấy thông tin chi tiết của video này.")
        return

    # Render details layout
    status = video.get('status', 'uploaded')
    status_color = "#10b981" if status in ["ready", "captioned"] else ("#f59e0b" if status == "processing" else "#ef4444")
    uname = video.get('author_name') or get_username(video['user_id'])
    
    st.markdown(f'<h1 class="gradient-title" style="text-align: left; font-size: 2rem; margin-top: 1rem; margin-bottom: 1.5rem;">{video["title"]}</h1>', unsafe_allow_html=True)

    c_left, c_right = st.columns([1.6, 1.4], gap="large")

    with c_left:
        # Large Player
        st.video(api_url(video["video_url"]))
        
        # User details card below video
        st.markdown(f"""
        <div class="comment-bubble" style="margin-top: 1.5rem;">
            <div style="display: flex; align-items: center; gap: 0.8rem;">
                <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #003087, #1a5cb0); display: flex; align-items: center; justify-content: center; font-weight: bold; color: white;">{uname[:2].upper()}</div>
                <div>
                    <div style="font-weight: 700; color: var(--text-primary);">{uname}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Đăng lúc: {format_datetime(video.get("created_at", ""))}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_right:
        # Status Badge
        st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <span style="font-size: 0.85rem; color: var(--text-muted);">Trạng thái:</span>
            <span style="background: rgba(255, 255, 255, 0.05); border: 1px solid {status_color}; color: {status_color}; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 20px; text-transform: uppercase;">{status}</span>
        </div>
        """, unsafe_allow_html=True)

        # Description
        if video.get("description"):
            st.markdown(f'<p style="color: var(--text-primary); font-size: 1rem; line-height: 1.5; margin-bottom: 1rem;">{video["description"]}</p>', unsafe_allow_html=True)

        # Hashtags
        if video.get("hashtags"):
            tags = video["hashtags"].split()
            tag_html = " ".join(f'<span style="background: rgba(168, 85, 247, 0.08); border: 1px solid rgba(168, 85, 247, 0.15); color: #c084fc; font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 6px; margin-right: 0.4rem; display: inline-block;">{tag}</span>' for tag in tags)
            st.markdown(f'<div style="margin-bottom: 1.5rem;">{tag_html}</div>', unsafe_allow_html=True)

        # AI Caption section
        st.markdown('<p style="font-family: \'Outfit\'; font-weight: 600; font-size: 0.95rem; color: var(--text-muted); margin-bottom: 0.5rem; text-transform: uppercase;">🤖 PHỤ ĐỀ AI & BẢN DỊCH</p>', unsafe_allow_html=True)
        caption_text = video.get("caption")
        if caption_text:
            st.markdown(f"""
            <div class="ai-caption-box" style="margin-top: 0; margin-bottom: 1rem;">
                <div class="ai-caption-content">{caption_text}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Chưa có phụ đề AI. Hãy bấm nút phía dưới để sinh phụ đề.")
            if st.button("🤖 Sinh mô tả video (AI)", key="detail_generate_caption", use_container_width=True):
                with st.spinner("AI đang xử lý..."):
                    cap_res = requests.post(api_url(f"/api/videos/{video['id']}/caption"), headers=auth_headers(), timeout=180)
                    if cap_res.ok:
                        st.success("Tạo caption AI thành công!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {cap_res.text}")

        # Comments Section
        st.markdown('<p style="font-family: \'Outfit\'; font-weight: 600; font-size: 0.95rem; color: var(--text-muted); margin-bottom: 0.5rem; text-transform: uppercase; margin-top: 1.5rem;">💬 BÌNH LUẬN</p>', unsafe_allow_html=True)
        try:
            c_res = requests.get(api_url(f"/api/comments/video/{video['id']}"), timeout=20)
            comments = c_res.json() if c_res.ok else []
        except Exception:
            comments = []

        comments_html = ""
        if not comments:
            comments_html = '<div style="color: var(--text-muted); font-size: 0.85rem; font-style: italic; text-align: center; padding: 1rem 0;">Chưa có bình luận nào.</div>'
        else:
            for c in comments:
                c_uname = get_username(c['user_id'])
                c_date = format_datetime(c.get('created_at', ''))
                safe_comment = html.escape(c['content'])
                comments_html += f'<div class="comment-bubble" style="margin-bottom: 0.5rem; padding: 0.6rem 0.8rem;"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;"><span class="comment-user" style="font-size: 0.8rem;">👤 {c_uname}</span><span style="font-size: 0.7rem; color: var(--text-muted);">{c_date}</span></div><div class="comment-text" style="font-size: 0.85rem; line-height: 1.3;">{safe_comment}</div></div>'
        st.markdown(f'<div class="comments-scroll-area" style="max-height: 300px;">{comments_html}</div>', unsafe_allow_html=True)

        if st.session_state.token:
            with st.form(key="detail_comment_form", clear_on_submit=True, border=False):
                col_inp, col_send = st.columns([4, 1])
                with col_inp:
                    content = st.text_input("Viết bình luận", label_visibility="collapsed", placeholder="Nhập bình luận...", max_chars=250, key="detail_c_inp")
                with col_send:
                    submitted = st.form_submit_button("💬", use_container_width=True)
                    if submitted and content.strip():
                        try:
                            requests.post(api_url(f"/api/comments/video/{video['id']}"), json={"content": content}, headers=auth_headers(), timeout=20)
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Thất bại: {exc}")
