import streamlit as st
import requests
from utils import api_url, auth_headers

def admin_users_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem; text-align: left;">👥 Quản lý Thành viên</h1>', unsafe_allow_html=True)
    
    try:
        res = requests.get(api_url("/api/admin/users"), headers=auth_headers(), timeout=20)
        users = res.json() if res.ok else []
    except Exception as exc:
        st.error(f"Không tải được danh sách thành viên: {exc}")
        users = []

    if not users:
        st.info("Chưa có thành viên nào.")
        return

    # Display users list
    for u in users:
        with st.container(border=True, key=f"admin_user_card_{u['id']}"):
            col_info, col_role_select, col_action = st.columns([2, 1, 1])
            with col_info:
                st.markdown(f"""
                <div>
                    <h3 style="margin: 0; font-size: 1.15rem; color: var(--text-primary);">{u['name']}</h3>
                    <div style="font-size: 0.85rem; color: var(--text-muted);">Email: {u['email']} | ID: {u['id']}</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col_role_select:
                roles = ["user", "admin"]
                current_role_idx = roles.index(u.get("role", "user")) if u.get("role", "user") in roles else 0
                new_role = st.selectbox(
                    "Vai trò",
                    roles,
                    index=current_role_idx,
                    key=f"role_sel_{u['id']}",
                    label_visibility="collapsed"
                )
                
            with col_action:
                if u.get("role", "user") != new_role:
                    if st.button("Lưu vai trò", key=f"role_save_{u['id']}", use_container_width=True):
                        try:
                            save_res = requests.post(
                                api_url(f"/api/admin/users/{u['id']}/role"),
                                json={"role": new_role},
                                headers=auth_headers(),
                                timeout=20
                            )
                            if save_res.ok:
                                st.success("Cập nhật vai trò thành công!")
                                if st.session_state.user and st.session_state.user["id"] == u["id"]:
                                    st.session_state.user["role"] = new_role
                                st.rerun()
                            else:
                                st.error(f"Cập nhật thất bại: {save_res.text}")
                        except Exception as exc:
                            st.error(f"Lỗi: {exc}")
                else:
                    st.markdown(f"<div style='text-align: center; color: #10b981; font-weight: 600; padding-top: 0.5rem;'>Hoạt động ({u.get('role', 'user').upper()})</div>", unsafe_allow_html=True)
