import os
import requests
import streamlit as st
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def auth_headers():
    if "token" in st.session_state and st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def api_url(path: str) -> str:
    return f"{BACKEND_URL}{path}"

def video_player_url(path: str) -> str:
    browser_url = os.getenv("BROWSER_BACKEND_URL")
    if browser_url:
        return f"{browser_url}{path}"
    url = api_url(path)
    if "://backend:" in url:
        return url.replace("://backend:", "://localhost:")
    return url

def get_username(user_id):
    if "token" in st.session_state and st.session_state.token and not st.session_state.users_map:
        try:
            res = requests.get(api_url("/api/users"), headers=auth_headers(), timeout=10)
            if res.ok:
                users = res.json()
                st.session_state.users_map = {u["id"]: u["name"] for u in users}
        except Exception:
            pass
    if "user" in st.session_state and st.session_state.user and st.session_state.user.get("id") == user_id:
        return st.session_state.user.get("name", f"Người dùng #{user_id}")
    return st.session_state.users_map.get(user_id, f"Người dùng #{user_id}")

def format_datetime(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%H:%M - %d/%m/%Y")
    except Exception:
        return dt_str
