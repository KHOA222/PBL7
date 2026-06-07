import streamlit as st
import requests
from utils import api_url, auth_headers

def profile_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem;">Trang cá nhân</h1>', unsafe_allow_html=True)
    
    if not st.session_state.user:
        col2 = st.container()
        with col2:
            st.warning("⚠️ Bạn chưa đăng nhập.")
            if st.button("Đăng nhập ngay", use_container_width=True):
                st.session_state.page = "Login"
                st.rerun()
    else:
        u = st.session_state.user
        
        # Query User's Videos
        try:
            res = requests.get(api_url("/api/videos"), timeout=20)
            my_videos = [v for v in (res.json() if res.ok else []) if v["user_id"] == u["id"]]
        except Exception as exc:
            st.error(f"Không tải được danh sách video: {exc}")
            my_videos = []

        total_videos = len(my_videos)
        captioned_videos = sum(1 for v in my_videos if v.get("caption"))

        # User Stats Card
        st.markdown(f"""<div class="sidebar-profile" style="max-width: 600px; margin: 0 auto 2.5rem auto; padding: 0; overflow: hidden; border-radius: 20px;">
<div class="profile-cover"></div>
<div style="padding: 1.5rem 2rem 2rem 2rem; position: relative;">
<div style="width: 90px; height: 90px; border-radius: 50%; background: linear-gradient(135deg, #003087, #FFB81C); display: flex; align-items: center; justify-content: center; font-size: 3rem; margin: -60px auto 0.8rem auto; border: 4px solid var(--avatar-border); box-shadow: 0 10px 25px rgba(0,0,0,0.4);">👤</div>
<div class="sidebar-profile-name" style="font-size: 1.8rem; margin-bottom: 0.2rem;">{u['name']}</div>
<div class="sidebar-profile-role" style="font-size: 0.95rem; margin-bottom: 1rem;">{u.get('role', 'user')}</div>
<div style="font-size: 0.95rem; color: var(--text-muted); margin-bottom: 1.5rem;">📧 Email: {u['email']}</div>
<div class="profile-stats">
<div class="stat-box">
<div class="stat-value">{total_videos}</div>
<div class="stat-label">Videos đã đăng</div>
</div>
<div class="stat-box">
<div class="stat-value">{captioned_videos}</div>
<div class="stat-label">Video có phụ đề AI</div>
</div>
</div>
</div>
</div>""", unsafe_allow_html=True)
        
        st.markdown('<h2 style="font-family: \'Outfit\'; font-size: 1.6rem; margin-bottom: 1.5rem; text-align: center;">🎬 Các video của tôi</h2>', unsafe_allow_html=True)
        
        if not my_videos:
            col2 = st.container()
            with col2:
                st.info("Bạn chưa tải video nào lên hệ thống.")
        else:
            # 2-Column Grid Layout for My Videos
            for i in range(0, len(my_videos), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(my_videos):
                        v = my_videos[i + j]
                        with cols[j]:
                            with st.container(border=True, key=f"my_video_card_{v['id']}"):
                                # Video Title
                                st.markdown(f'<h3 style="font-family: \'Outfit\'; font-size: 1.3rem; margin-top: 0; margin-bottom: 0.4rem; color: var(--text-primary);">{v["title"] or "(không tiêu đề)"}</h3>', unsafe_allow_html=True)
                                
                                status_color = "#10b981" if v['status'] in ["ready", "captioned"] else ("#f59e0b" if v['status'] == "processing" else "#ef4444")
                                st.markdown(f"""
                                <div style="margin-bottom: 0.8rem;">
                                    <span style="font-size: 0.75rem; color: var(--text-muted);">ID: {v['id']}</span>
                                    <span style="margin-left: 0.8rem; background: rgba(255, 255, 255, 0.05); border: 1px solid {status_color}; color: {status_color}; font-size: 0.7rem; font-weight: 600; padding: 0.1rem 0.4rem; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.05em;">
                                        {v['status']}
                                    </span>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Mini Description
                                if v.get("description"):
                                    desc = v["description"]
                                    short_desc = desc[:100] + "..." if len(desc) > 100 else desc
                                    st.markdown(f'<p style="color: var(--text-muted); font-size: 0.85rem; line-height: 1.4; margin-bottom: 0.8rem;">{short_desc}</p>', unsafe_allow_html=True)
                                
                                # Video Player (Medium size)
                                video_url = api_url(v["video_url"])
                                st.video(video_url)
                                
                                # AI Caption Box
                                if v.get("caption"):
                                    st.markdown(f"""
                                    <div class="ai-caption-box" style="padding: 0.8rem; margin: 0.8rem 0; font-size: 0.85rem;">
                                        <div class="ai-caption-header" style="margin-bottom: 0.3rem;">
                                            <span class="ai-badge" style="font-size: 0.65rem; padding: 0.15rem 0.45rem;">🤖 Phụ đề AI</span>
                                        </div>
                                        <div class="ai-caption-content" style="font-size: 0.85rem;">{v['caption']}</div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.markdown("""
                                    <div style="background: rgba(245, 158, 11, 0.05); border: 1px dashed rgba(245, 158, 11, 0.2); border-radius: 8px; padding: 0.6rem; margin: 0.8rem 0; text-align: center;">
                                        <span style="color: #fbbf24; font-weight: 600; font-size: 0.85rem; font-family: 'Outfit';">⚠️ Chưa sinh phụ đề AI</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                # Actions Row
                                st.markdown("<div style='margin-top: 0.8rem;'></div>", unsafe_allow_html=True)
                                c_act1, c_act2 = st.columns([1, 1])
                                with c_act1:
                                    edit_key = f"show_edit_{v['id']}"
                                    if edit_key not in st.session_state:
                                        st.session_state[edit_key] = False
                                    if st.button("✏️ Chỉnh sửa", key=f"pedit_toggle_{v['id']}", use_container_width=True):
                                        st.session_state[edit_key] = not st.session_state[edit_key]
                                with c_act2:
                                    if st.button("🗑️ Xóa video", key=f"pdel_{v['id']}", use_container_width=True):
                                        with st.spinner("Đang xóa video..."):
                                            r = requests.delete(api_url(f"/api/videos/{v['id']}"), headers=auth_headers(), timeout=20)
                                            if r.ok:
                                                st.success("Đã xóa video thành công!")
                                                st.rerun()
                                            else:
                                                st.error(r.text)
                                if st.session_state.get(edit_key, False):
                                    with st.form(key=f"edit_form_{v['id']}", border=True):
                                        new_title = st.text_input("Tiêu đề", value=v.get("title", ""), key=f"et_{v['id']}")
                                        new_desc = st.text_area("Mô tả", value=v.get("description", "") or "", key=f"ed_{v['id']}", height=80)
                                        new_tags = st.text_input("Hashtag", value=v.get("hashtags", "") or "", key=f"eh_{v['id']}")
                                        if st.form_submit_button("💾 Lưu", use_container_width=True):
                                            r = requests.patch(
                                                api_url(f"/api/videos/{v['id']}"),
                                                json={"title": new_title, "description": new_desc, "hashtags": new_tags},
                                                headers=auth_headers(),
                                                timeout=20,
                                            )
                                            if r.ok:
                                                st.session_state[edit_key] = False
                                                st.success("Đã cập nhật!")
                                                st.rerun()
                                            else:
                                                st.error(r.text)
