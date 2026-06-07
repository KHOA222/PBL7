import streamlit as st
import requests
from utils import api_url, auth_headers

def admin_dashboard_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem; text-align: left;">📊 Admin Dashboard</h1>', unsafe_allow_html=True)
    
    try:
        res = requests.get(api_url("/api/admin/stats"), headers=auth_headers(), timeout=20)
        stats = res.json() if res.ok else {}
    except Exception as exc:
        st.error(f"Không kết nối được API admin stats: {exc}")
        stats = {}

    if not stats:
        st.warning("Không tải được thông tin thống kê.")
        return

    # Display Stat Cards
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True, key="stat_card_users"):
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <div style="font-size: 1rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">👥 Tổng thành viên</div>
                <div style="font-size: 2.8rem; font-weight: 800; color: #8b5cf6; margin: 0.5rem 0;">{stats.get("total_users", 0)}</div>
            </div>
            """, unsafe_allow_html=True)
    with c2:
        with st.container(border=True, key="stat_card_videos"):
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <div style="font-size: 1rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">🎬 Tổng số video</div>
                <div style="font-size: 2.8rem; font-weight: 800; color: #ec4899; margin: 0.5rem 0;">{stats.get("total_videos", 0)}</div>
            </div>
            """, unsafe_allow_html=True)
    with c3:
        with st.container(border=True, key="stat_card_model"):
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <div style="font-size: 1rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">🤖 Model hiện tại</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #06b6d4; margin: 0.8rem 0;">{stats.get("active_model_version", "N/A")}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # Caption moderation stats
    reviews = stats.get("caption_reviews", {})
    st.markdown('<h2 style="font-family: \'Outfit\'; font-size: 1.5rem; margin-bottom: 1rem;">✍️ Trạng thái duyệt Phụ đề</h2>', unsafe_allow_html=True)
    
    col_p, col_a, col_r = st.columns(3)
    with col_p:
        with st.container(border=True, key="stat_card_pending"):
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <div style="font-size: 0.9rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">⌛ Chờ duyệt</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #f59e0b; margin: 0.4rem 0;">{reviews.get("pending", 0)}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Đi đến Duyệt Caption", key="goto_caption_moderation", use_container_width=True):
                st.session_state.page = "Admin Caption Review"
                st.rerun()
                
    with col_a:
        with st.container(border=True, key="stat_card_approved"):
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <div style="font-size: 0.9rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">✅ Đã chấp thuận</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #10b981; margin: 0.4rem 0;">{reviews.get("approved", 0)}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Xem Dataset huấn luyện", key="goto_dataset_management", use_container_width=True):
                st.session_state.page = "Admin Dataset"
                st.rerun()
                
    with col_r:
        with st.container(border=True, key="stat_card_rejected"):
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem;">
                <div style="font-size: 0.9rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">❌ Đã từ chối</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #ef4444; margin: 0.4rem 0;">{reviews.get("rejected", 0)}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Quản lý Huấn luyện", key="goto_training_management", use_container_width=True):
                st.session_state.page = "Admin Training"
                st.rerun()
