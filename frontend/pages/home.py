import streamlit as st
import requests
import html
from utils import api_url, auth_headers, get_username, format_datetime

def home_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem;">Bảng tin Video</h1>', unsafe_allow_html=True)

    # Process pending caption request BEFORE rendering (outside the loop)
    pending_id = st.session_state.pop("pending_caption_video_id", None)
    if pending_id:
        with st.spinner("Đang chạy AI caption engine..."):
            cap_res = requests.post(
                api_url(f"/api/videos/{pending_id}/caption"),
                headers=auth_headers(),
                timeout=180,
            )
            if cap_res.ok:
                st.session_state.revealed_captions.add(pending_id)
                st.success("Tạo caption AI thành công!")
            else:
                st.error(f"Lỗi: {cap_res.text}")

    try:
        res = requests.get(api_url("/api/videos"), timeout=20)
        videos = res.json() if res.ok else []
    except Exception as exc:
        st.error(f"Không tải được feed: {exc}")
        videos = []

    # Fetch all comments in a single query to avoid N+1 API requests on feed load
    comments_by_video = {}
    try:
        c_res = requests.get(api_url("/api/comments"), timeout=20)
        if c_res.ok:
            for c in c_res.json():
                comments_by_video.setdefault(c["video_id"], []).append(c)
    except Exception:
        pass

    col2 = st.container()
    with col2:
        if not videos:
            st.info("Chưa có video nào trên hệ thống. Hãy đăng video đầu tiên của bạn!")
            if st.button("Đi đến trang Upload", use_container_width=True):
                st.session_state.page = "Upload"
                st.rerun()
        else:
            # Search & Filter Layout
            col_search, col_sort = st.columns([3, 1])
            with col_search:
                search_query = st.text_input("🔍 Tìm kiếm tiêu đề hoặc hashtag...", placeholder="Nhập từ khóa hoặc #tag...", label_visibility="collapsed", key="feed_search")
            with col_sort:
                sort_order = st.selectbox("Sắp xếp", ["Mới nhất", "Cũ nhất"], index=0, label_visibility="collapsed", key="feed_sort")
                
            # Filter implementation
            if search_query:
                query = search_query.lower()
                videos = [
                    v for v in videos
                    if query in v["title"].lower()
                    or (v.get("description") and query in v["description"].lower())
                    or (v.get("hashtags") and query in v["hashtags"].lower())
                ]
                
            # Sort implementation
            if sort_order == "Cũ nhất":
                videos = sorted(videos, key=lambda x: x.get("created_at", ""))
            else:
                videos = sorted(videos, key=lambda x: x.get("created_at", ""), reverse=True)

            if not videos:
                st.warning("Không tìm thấy video nào phù hợp với từ khóa tìm kiếm của bạn.")
            else:
                for video in videos:
                    with st.container(border=True, key=f"video_card_{video['id']}"):
                        # Video Card Header
                        status = video.get('status', 'uploaded')
                        status_color = "#10b981" if status in ["ready", "captioned"] else ("#f59e0b" if status == "processing" else "#ef4444")
                        uname = video.get('author_name') or get_username(video['user_id'])
                        avatar_letters = uname[:2].upper() if uname else "??"
                        
                        header_html = f'<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.2rem; border-bottom: 1px solid var(--card-border); padding-bottom: 0.8rem;"><div style="display: flex; align-items: center; gap: 0.8rem;"><div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #003087, #1a5cb0); display: flex; align-items: center; justify-content: center; font-weight: bold; font-family: \'Outfit\'; color: white; font-size: 1.1rem; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">{avatar_letters}</div><div><div style="font-weight: 700; font-family: \'Outfit\'; font-size: 1.1rem; color: var(--text-primary);">{uname}</div><div style="font-size: 0.75rem; color: var(--text-muted);">ID Video: {video["id"]}</div></div></div><span style="background: rgba(255, 255, 255, 0.05); border: 1px solid {status_color}; color: {status_color}; font-size: 0.7rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 20px; font-family: \'Outfit\'; text-transform: uppercase; letter-spacing: 0.05em;">{status}</span></div>'
                        st.markdown(header_html, unsafe_allow_html=True)
                        
                        # Split columns inside the card
                        c_left, c_right = st.columns([1.6, 1.4], gap="medium")
                        
                        with c_left:
                            # Video Player
                            video_url = api_url(video["video_url"])
                            st.video(video_url)
                            
                            # AI Caption Button inside Left column (if not revealed yet)
                            if video["id"] not in st.session_state.revealed_captions:
                                if status == "processing":
                                    st.info("🤖 AI đang phân tích và sinh phụ đề cho video này...")
                                else:
                                    if st.session_state.token:
                                        if st.button("🤖 Sinh mô tả video (AI)", key=f"cap_{video['id']}", use_container_width=True):
                                            if video.get("caption"):
                                                st.session_state.revealed_captions.add(video["id"])
                                                st.rerun()
                                            else:
                                                st.session_state.pending_caption_video_id = video["id"]
                                                st.rerun()
                                    else:
                                        st.caption("🔒 Đăng nhập để sử dụng tính năng sinh phụ đề AI.")
                                        
                        with c_right:
                            # Video Title
                            st.markdown(f'<h3 style="font-family: \'Outfit\', sans-serif; font-size: 1.3rem; margin-top: 0; margin-bottom: 0.4rem; color: var(--text-primary);">{video["title"]}</h3>', unsafe_allow_html=True)
                            
                            # Video Description
                            if video.get("description"):
                                st.markdown(f'<p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 0.6rem; line-height: 1.4;">{video["description"]}</p>', unsafe_allow_html=True)
                            
                            # Video Hashtags
                            if video.get("hashtags"):
                                tags = video["hashtags"].split()
                                tag_html = " ".join(f'<span style="background: rgba(168, 85, 247, 0.08); border: 1px solid rgba(168, 85, 247, 0.15); color: #c084fc; font-size: 0.75rem; padding: 0.1rem 0.4rem; border-radius: 6px; font-family: \'Outfit\'; margin-right: 0.3rem; display: inline-block;">{tag}</span>' for tag in tags)
                                st.markdown(f'<div style="margin-bottom: 0.8rem;">{tag_html}</div>', unsafe_allow_html=True)
                            
                            # AI Caption Box display (if revealed)
                            if video["id"] in st.session_state.revealed_captions:
                                caption_text = video.get("caption", "")
                                if caption_text:
                                    caption_html = f'<div class="ai-caption-box" style="margin: 0 0 1rem 0; padding: 0.8rem 1rem;"><div class="ai-caption-header" style="margin-bottom: 0.4rem;"><span class="ai-badge" style="font-size: 0.65rem; padding: 0.15rem 0.45rem;">🤖 Phụ đề AI</span></div><div class="ai-caption-content" style="font-size: 0.85rem; line-height: 1.4;">{caption_text}</div></div>'
                                    st.markdown(caption_html, unsafe_allow_html=True)
                                else:
                                    st.info("🤖 Không tìm thấy phụ đề cho video này hoặc đang xử lý...")
                            
                            # Comments Section Header
                            st.markdown('<p style="font-family: \'Outfit\'; font-weight: 600; font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">💬 Thảo luận</p>', unsafe_allow_html=True)
                            
                            # Fetch Comments from pre-fetched batch dictionary
                            comments = comments_by_video.get(video["id"], [])
                                
                            # Scrollable comments area
                            comments_html = ""
                            if not comments:
                                comments_html = '<div style="color: var(--text-muted); font-size: 0.85rem; font-style: italic; text-align: center; padding: 1.5rem 0;">Chưa có bình luận nào. Hãy là người đầu tiên!</div>'
                            else:
                                for c in comments:
                                    c_uname = get_username(c['user_id'])
                                    c_date = format_datetime(c.get('created_at', ''))
                                    safe_comment = html.escape(c['content'])
                                    comments_html += f'<div class="comment-bubble" style="margin-bottom: 0.6rem; padding: 0.6rem 0.8rem;"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;"><span class="comment-user" style="font-size: 0.8rem;">👤 {c_uname}</span><span style="font-size: 0.75rem; color: var(--text-muted);">{c_date}</span></div><div class="comment-text" style="font-size: 0.85rem; line-height: 1.3;">{safe_comment}</div></div>'
                            st.markdown(f'<div class="comments-scroll-area">{comments_html}</div>', unsafe_allow_html=True)
                            
                            # Send comment input form
                            if st.session_state.token:
                                with st.form(key=f"comment_form_{video['id']}", clear_on_submit=True, border=False):
                                    col_inp, col_send = st.columns([4, 1])
                                    with col_inp:
                                        content = st.text_input("Viết bình luận", label_visibility="collapsed", placeholder="Nhập bình luận (tối đa 250 ký tự)...", max_chars=250, key=f"c_inp_txt_{video['id']}")
                                    with col_send:
                                        submitted = st.form_submit_button("💬", use_container_width=True)
                                        if submitted and content.strip():
                                            try:
                                                requests.post(
                                                    api_url(f"/api/comments/video/{video['id']}"),
                                                    json={"content": content},
                                                    headers=auth_headers(),
                                                    timeout=20,
                                                )
                                                st.rerun()
                                            except Exception as exc:
                                                st.error(f"Thất bại: {exc}")
                            else:
                                st.caption("🔒 Bạn cần đăng nhập để viết bình luận.")
