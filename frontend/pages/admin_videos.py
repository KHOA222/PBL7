import streamlit as st
import requests
from utils import api_url, auth_headers, get_username, video_player_url

def admin_videos_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem; text-align: left;">🎬 Quản lý Video</h1>', unsafe_allow_html=True)
    
    try:
        res = requests.get(api_url("/api/admin/videos"), headers=auth_headers(), timeout=20)
        videos = res.json() if res.ok else []
    except Exception as exc:
        st.error(f"Không tải được danh sách video: {exc}")
        videos = []

    if not videos:
        st.info("Chưa có video nào trên hệ thống.")
        return

    # List videos
    for v in videos:
        with st.container(border=True, key=f"admin_video_card_{v['id']}"):
            c_left, c_right = st.columns([1.5, 1.5], gap="medium")
            
            with c_left:
                st.video(video_player_url(v["video_url"]))
                
            with c_right:
                st.markdown(f"""
                <h3 style="margin-top: 0; margin-bottom: 0.5rem; font-size: 1.25rem; color: var(--text-primary);">{v['title']}</h3>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.8rem;">
                    Người đăng: <b>{get_username(v['user_id'])}</b> | ID Video: {v['id']}
                </div>
                """, unsafe_allow_html=True)
                
                if v.get("description"):
                    st.markdown(f'<p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.4; margin-bottom: 0.8rem;">{v["description"]}</p>', unsafe_allow_html=True)
                    
                status_color = "#10b981" if v['status'] in ["ready", "captioned"] else ("#f59e0b" if v['status'] == "processing" else "#ef4444")
                st.markdown(f"""
                <div style="margin-bottom: 1rem;">
                    <span style="font-size: 0.85rem; color: var(--text-muted);">Trạng thái:</span>
                    <span style="background: rgba(255, 255, 255, 0.05); border: 1px solid {status_color}; color: {status_color}; font-size: 0.7rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: 20px; text-transform: uppercase;">
                        {v['status']}
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                # Delete Action
                if st.button("🗑️ Xóa video khỏi hệ thống", key=f"admin_del_{v['id']}", use_container_width=True):
                    with st.spinner("Đang xóa video..."):
                        try:
                            del_res = requests.delete(
                                api_url(f"/api/videos/{v['id']}"),
                                headers=auth_headers(),
                                timeout=20
                            )
                            if del_res.ok:
                                st.success("Đã xóa video thành công!")
                                st.rerun()
                            else:
                                st.error(f"Xóa video thất bại: {del_res.text}")
                        except Exception as exc:
                            st.error(f"Lỗi: {exc}")
