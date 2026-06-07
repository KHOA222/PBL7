import streamlit as st
import requests
import json
from utils import api_url, auth_headers

def _save_cookie(token: str, user: dict):
    import os, time
    session_file = os.path.join(os.path.dirname(__file__), "..", ".session.json")
    with open(session_file, "w") as f:
        json.dump({"token": token, "user": user, "ts": time.time()}, f)

def login_page():
    col_title, col_theme = st.columns([4, 1])
    with col_title:
        st.markdown('<h1 style="font-family: \'Outfit\', sans-serif; font-weight: 800; margin-top: 0.2rem; margin-bottom: 1.5rem; font-size: 2.4rem; text-align: left; display: flex; align-items: center; gap: 0.8rem; color: var(--text-primary) !important;"><span style="flex-shrink: 0;">🎬</span><span class="gradient-title" style="display: inline-block; text-align: left;">VideoSocial</span></h1>', unsafe_allow_html=True)
    with col_theme:
        theme_icon = "☀️" if st.session_state.theme == "Dark" else "🌙"
        if st.button(theme_icon, key="login_theme_btn", help="Chuyển đổi giao diện"):
            st.session_state.theme = "Light" if st.session_state.theme == "Dark" else "Dark"
            st.rerun()
    
    def _parse_error(res) -> str:
        try:
            body = res.json()
            if "detail" in body:
                detail = body["detail"]
                if isinstance(detail, list):
                    return "; ".join(e.get("msg", str(e)) for e in detail)
                return str(detail)
        except Exception:
            pass
        return res.text

    tab_login, tab_register = st.tabs(["🔒 Đăng nhập", "📝 Đăng ký"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mật khẩu", type="password", key="login_password")
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        if st.button("Đăng nhập", key="submit_login", use_container_width=True):
            try:
                res = requests.post(
                    api_url("/api/auth/login"),
                    data={"username": email.strip().lower(), "password": password},
                    timeout=20,
                )
                if res.ok:
                    data = res.json()
                    st.session_state.token = data["access_token"]
                    st.session_state.user = data["user"]
                    st.session_state.users_map = {}
                    _save_cookie(data["access_token"], data["user"])
                    if data["user"].get("role") == "admin":
                        st.session_state.page = "Admin Dashboard"
                    else:
                        st.session_state.page = "Home Feed"
                    st.success("Đăng nhập thành công!")
                    st.rerun()
                else:
                    st.error(_parse_error(res))
            except Exception as exc:
                st.error(f"Không kết nối được backend: {exc}")

    with tab_register:
        name = st.text_input("Tên hiển thị", key="register_name")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Mật khẩu", type="password", key="register_password")
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        if st.button("Đăng ký", key="submit_register", use_container_width=True):
            try:
                res = requests.post(
                    api_url("/api/auth/register"),
                    json={"name": name.strip(), "email": email.strip().lower(), "password": password},
                    timeout=20,
                )
                if res.ok:
                    data = res.json()
                    st.session_state.token = data["access_token"]
                    st.session_state.user = data["user"]
                    st.session_state.users_map = {}
                    _save_cookie(data["access_token"], data["user"])
                    st.session_state.page = "Home Feed"
                    st.success("Đăng ký thành công!")
                    st.rerun()
                else:
                    st.error(_parse_error(res))
            except Exception as exc:
                st.error(f"Không kết nối được backend: {exc}")
