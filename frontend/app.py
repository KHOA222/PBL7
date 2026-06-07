import os
import time
import json
import requests
import streamlit as st

# Set page config FIRST before any other streamlit calls
st.set_page_config(page_title="Video Social App", page_icon="🎬", layout="wide")

INACTIVITY_TIMEOUT = 5 * 60  # 5 phút
_SESSION_FILE = os.path.join(os.path.dirname(__file__), ".session.json")

def _save_session(token: str, user: dict):
    with open(_SESSION_FILE, "w") as f:
        json.dump({"token": token, "user": user, "ts": time.time()}, f)

def _clear_session():
    if os.path.exists(_SESSION_FILE):
        os.remove(_SESSION_FILE)

def _load_session() -> dict | None:
    if not os.path.exists(_SESSION_FILE):
        return None
    try:
        with open(_SESSION_FILE) as f:
            data = json.load(f)
        if time.time() - data.get("ts", 0) > INACTIVITY_TIMEOUT:
            _clear_session()
            return None
        return data
    except Exception:
        return None

# Initialize Session State defaults
for _k, _v in [("token", None), ("user", None), ("revealed_captions", set()), ("users_map", {}), ("theme", "Light"), ("last_active", time.time())]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Restore from disk on fresh session
if st.session_state.token is None:
    saved = _load_session()
    if saved:
        st.session_state.token = saved["token"]
        st.session_state.user = saved.get("user")
        st.session_state.last_active = time.time()

# Auto-logout after inactivity + refresh session file timestamp
if st.session_state.token:
    if time.time() - st.session_state.last_active > INACTIVITY_TIMEOUT:
        _clear_session()
        st.session_state.token = None
        st.session_state.user = None
        st.session_state.page = "Login"
        st.warning("Phiên đăng nhập hết hạn do không hoạt động. Vui lòng đăng nhập lại.")
    else:
        st.session_state.last_active = time.time()
        _save_session(st.session_state.token, st.session_state.user or {})
        st.session_state.last_active = time.time()

# Force page to Login if not authenticated
if not st.session_state.token:
    st.session_state.page = "Login"
elif "page" not in st.session_state or st.session_state.page == "Login":
    st.session_state.page = "Home Feed"

# Reset revealed captions when navigating away from and back to Home Feed
_prev_page = st.session_state.get("_prev_page", "")
_cur_page = st.session_state.get("page", "")
if _cur_page != _prev_page:
    if _cur_page == "Home Feed":
        st.session_state.revealed_captions = set()
    st.session_state._prev_page = _cur_page

# Import page modules
from utils import api_url, auth_headers
from pages.login import login_page
from pages.home import home_page
from pages.upload import upload_page
from pages.profile import profile_page
from pages.video_detail import video_detail_page
from pages.admin_dashboard import admin_dashboard_page
from pages.admin_users import admin_users_page
from pages.admin_videos import admin_videos_page
from pages.admin_caption_review import admin_caption_review_page
from pages.admin_dataset import admin_dataset_page
from pages.admin_training import admin_training_page
from pages.admin_model_evaluation import admin_model_evaluation_page

# Helper to inject CSS and background decoration
def inject_custom_styles():
    css_file = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_file):
        with open(css_file, "r", encoding="utf-8") as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
            
    # Inject background decorative glowing blobs for unique modern mesh effect
    st.markdown("""
    <div class="bg-glow bg-glow-1"></div>
    <div class="bg-glow bg-glow-2"></div>
    <div class="bg-glow bg-glow-3"></div>
    """, unsafe_allow_html=True)
            
    # Inject variables for current theme
    if st.session_state.theme == "Light":
        st.markdown("""
        <style>
            :root {
                --bg-gradient: #F0F4FA !important;
                --text-primary: #001233 !important;
                --text-secondary: #1a3a5c !important;
                --text-muted: #4a6e94 !important;
                --sidebar-bg: #ffffff !important;
                --sidebar-border: #003087 !important;
                --card-bg: #ffffff !important;
                --card-border: #ccd9ee !important;
                --card-shadow: 0 2px 12px rgba(0,48,135,0.08) !important;
                --card-hover-border: #003087 !important;
                --card-hover-shadow: 0 4px 20px rgba(0,48,135,0.15) !important;
                --btn-secondary-bg: #f0f4fa !important;
                --btn-secondary-border: #ccd9ee !important;
                --btn-secondary-text: #003087 !important;
                --input-bg: #ffffff !important;
                --input-border: #ccd9ee !important;
                --input-text: #001233 !important;
                --comment-bg: #f7f9fc !important;
                --comment-border: #dce8f5 !important;
                --ai-box-bg: #eef3fb !important;
                --ai-box-border: #003087 !important;
                --profile-cover: #003087 !important;
                --avatar-border: #ffffff !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            :root {
                --bg-gradient: #001233 !important;
                --text-primary: #ffffff !important;
                --text-secondary: #c8d8e8 !important;
                --text-muted: #7a9ab5 !important;
                --sidebar-bg: #002060 !important;
                --sidebar-border: #FFB81C !important;
                --card-bg: #002060 !important;
                --card-border: #1a4080 !important;
                --card-shadow: 0 2px 12px rgba(0,0,0,0.3) !important;
                --card-hover-border: #FFB81C !important;
                --card-hover-shadow: 0 4px 20px rgba(255,184,28,0.15) !important;
                --btn-secondary-bg: #002a6e !important;
                --btn-secondary-border: #1a4080 !important;
                --btn-secondary-text: #c8d8e8 !important;
                --input-bg: #002060 !important;
                --input-border: #1a4080 !important;
                --input-text: #ffffff !important;
                --comment-bg: #002a6e !important;
                --comment-border: #1a4080 !important;
                --ai-box-bg: #002a6e !important;
                --ai-box-border: #FFB81C !important;
                --profile-cover: #FFB81C !important;
                --avatar-border: #001233 !important;
            }
        </style>
        """, unsafe_allow_html=True)

    # Hide sidebar globally or style Login Page Block
    if not st.session_state.token:
        st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            [data-testid="stSidebarCollapsedControl"] {
                display: none !important;
            }
            [data-testid="stHeader"] {
                display: none !important;
            }
            .block-container {
                max-width: 580px !important;
                background: rgba(15, 12, 27, 0.65) !important;
                backdrop-filter: blur(20px) !important;
                border: 1px solid rgba(255, 255, 255, 0.08) !important;
                border-radius: 24px !important;
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5) !important;
                padding: 3rem 2.5rem !important;
                margin: 10vh auto !important;
                float: none !important;
                position: relative !important;
            }
        </style>
        """, unsafe_allow_html=True)
        if st.session_state.theme == "Light":
            st.markdown("""
            <style>
                .block-container {
                    background: rgba(255, 255, 255, 0.65) !important;
                    border: 1px solid rgba(0, 0, 0, 0.06) !important;
                    box-shadow: 0 20px 50px rgba(31, 38, 135, 0.08) !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
    if st.session_state.token:
        st.markdown("""
        <style>
            .block-container {
                padding-top: 6.5rem !important;
            }
        </style>
        """, unsafe_allow_html=True)

inject_custom_styles()

page = st.session_state.page

# --- NAVIGATION BARS ---
if page != "Login" and st.session_state.token:
    user = st.session_state.user or {}
    is_admin = user.get("role") == "admin"
    
    # RENDER ADMIN NAVBAR
    if page.startswith("Admin"):
        with st.container(key="top_navbar"):
            cols = st.columns([1.5, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 1.1, 0.5, 0.8])
            (
                col_logo, col_db, col_users, col_vids, col_caps, 
                col_ds, col_train, col_eval, col_view_app, col_theme, col_logout
            ) = cols
            
            with col_logo:
                st.markdown('<h2 style="font-family: \'Outfit\'; font-size: 1.6rem; margin-top: 0; margin-bottom: 0; font-weight: 800; line-height: 2.2rem; display: flex; align-items: center; gap: 0.5rem; color: var(--text-primary) !important;"><span style="flex-shrink: 0;">🛠️</span><span style="background: linear-gradient(135deg, #003087, #FFB81C); -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; color: transparent !important; display: inline-block;">Admin</span></h2>', unsafe_allow_html=True)
                
            with col_db:
                is_active = page == "Admin Dashboard"
                if st.button("📊 Stats", key="nav_admin_db", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Admin Dashboard"
                    st.rerun()
            with col_users:
                is_active = page == "Admin Users"
                if st.button("👥 Users", key="nav_admin_users", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Admin Users"
                    st.rerun()
            with col_vids:
                is_active = page == "Admin Videos"
                if st.button("🎬 Vids", key="nav_admin_vids", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Admin Videos"
                    st.rerun()
            with col_caps:
                is_active = page == "Admin Caption Review"
                if st.button("📝 Caps", key="nav_admin_caps", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Admin Caption Review"
                    st.rerun()
            with col_ds:
                is_active = page == "Admin Dataset"
                if st.button("📂 Data", key="nav_admin_ds", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Admin Dataset"
                    st.rerun()
            with col_train:
                is_active = page == "Admin Training"
                if st.button("🧠 Train", key="nav_admin_train", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Admin Training"
                    st.rerun()
            with col_eval:
                is_active = page == "Admin Model Evaluation"
                if st.button("🤖 Deploy", key="nav_admin_eval", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Admin Model Evaluation"
                    st.rerun()
            with col_view_app:
                if st.button("🌐 Bảng tin", key="nav_admin_view_app", use_container_width=True, type="secondary"):
                    st.session_state.page = "Home Feed"
                    st.rerun()
            with col_theme:
                theme_icon = "☀️" if st.session_state.theme == "Dark" else "🌙"
                if st.button(theme_icon, key="top_theme_btn", use_container_width=True):
                    st.session_state.theme = "Light" if st.session_state.theme == "Dark" else "Dark"
                    st.rerun()
            with col_logout:
                if st.button("🚪 Thoát", key="top_logout_btn", use_container_width=True):
                    _clear_session()
                    st.session_state.token = None
                    st.session_state.user = None
                    st.session_state.users_map = {}
                    st.session_state.page = "Login"
                    st.rerun()
    # RENDER USER NAVBAR
    else:
        with st.container(key="top_navbar"):
            if is_admin:
                cols = st.columns([1.5, 1.0, 1.0, 1.0, 1.2, 0.6, 0.8])
                col_logo, col_nav1, col_nav2, col_nav3, col_admin, col_theme, col_logout = cols
            else:
                cols = st.columns([2.0, 1.2, 1.2, 1.2, 0.7, 1.0])
                col_logo, col_nav1, col_nav2, col_nav3, col_theme, col_logout = cols
                
            with col_logo:
                st.markdown('<h2 style="font-family: \'Outfit\'; font-size: 1.6rem; margin-top: 0; margin-bottom: 0; font-weight: 800; line-height: 2.2rem; display: flex; align-items: center; gap: 0.5rem; color: var(--text-primary) !important;"><span style="flex-shrink: 0;">🎬</span><span style="background: linear-gradient(135deg, #003087, #FFB81C); -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; color: transparent !important; display: inline-block;">VideoSocial</span></h2>', unsafe_allow_html=True)
                
            with col_nav1:
                is_active = page == "Home Feed"
                if st.button("🏠 Trang chủ", key="nav_home", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Home Feed"
                    st.session_state.revealed_captions = set()
                    st.rerun()
            with col_nav2:
                is_active = page == "Upload"
                if st.button("📤 Tải video", key="nav_upload", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Upload"
                    st.session_state.revealed_captions = set()
                    st.rerun()
            with col_nav3:
                is_active = page == "Profile"
                if st.button("👤 Cá nhân", key="nav_profile", use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.page = "Profile"
                    st.session_state.revealed_captions = set()
                    st.rerun()
            if is_admin:
                with col_admin:
                    if st.button("🛠️ Admin Panel", key="nav_admin_panel", use_container_width=True, type="secondary"):
                        st.session_state.page = "Admin Dashboard"
                        st.rerun()
            with col_theme:
                theme_icon = "☀️" if st.session_state.theme == "Dark" else "🌙"
                if st.button(theme_icon, key="top_theme_btn", use_container_width=True):
                    st.session_state.theme = "Light" if st.session_state.theme == "Dark" else "Dark"
                    st.rerun()
            with col_logout:
                if st.button("🚪 Thoát", key="top_logout_btn", use_container_width=True):
                    _clear_session()
                    st.session_state.token = None
                    st.session_state.user = None
                    st.session_state.users_map = {}
                    st.session_state.page = "Login"
                    st.rerun()

# --- RENDER PAGES ---
if page == "Login":
    login_page()
elif page == "Home Feed":
    home_page()
elif page == "Upload":
    upload_page()
elif page == "Profile":
    profile_page()
elif page == "Video Detail":
    video_detail_page()
elif page == "Admin Dashboard":
    admin_dashboard_page()
elif page == "Admin Users":
    admin_users_page()
elif page == "Admin Videos":
    admin_videos_page()
elif page == "Admin Caption Review":
    admin_caption_review_page()
elif page == "Admin Dataset":
    admin_dataset_page()
elif page == "Admin Training":
    admin_training_page()
elif page == "Admin Model Evaluation":
    admin_model_evaluation_page()
