import streamlit as st
import requests
from utils import api_url, auth_headers

def admin_dataset_page():
    st.markdown('<h1 class="gradient-title" style="margin-top: 2rem; margin-bottom: 2rem; text-align: left;">📂 Dữ liệu Huấn luyện (Dataset)</h1>', unsafe_allow_html=True)
    
    # Query stats
    try:
        res = requests.get(api_url("/api/admin/dataset/stats"), headers=auth_headers(), timeout=20)
        stats = res.json() if res.ok else {}
    except Exception as exc:
        st.error(f"Lỗi tải thống kê dataset: {exc}")
        stats = {}

    if stats:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True, key="ds_total_card"):
                st.metric("Tổng số mẫu (Samples)", stats.get("total_samples", 0))
        with c2:
            with st.container(border=True, key="ds_active_card"):
                st.metric("Mẫu khả dụng (Active)", stats.get("active_samples", 0))

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # Form to add approved caption manually
    with st.container(border=True, key="add_dataset_form"):
        st.markdown("<h3>➕ Thêm mẫu dữ liệu thủ công</h3>", unsafe_allow_html=True)
        vid_id = st.number_input("ID Video", min_value=1, step=1, key="add_ds_vid_id")
        caption_text = st.text_area("Nội dung mô tả (Caption Text)", placeholder="Nhập phụ đề mô tả chuẩn xác cho video này...", key="add_ds_caption")
        
        if st.button("Lưu vào Dataset", key="save_to_dataset_btn", use_container_width=True):
            if not caption_text.strip():
                st.error("Vui lòng nhập nội dung mô tả!")
            else:
                try:
                    save_res = requests.post(
                        api_url("/api/admin/dataset/add-approved-caption"),
                        json={"video_id": int(vid_id), "caption_text": caption_text.strip()},
                        headers=auth_headers(),
                        timeout=20
                    )
                    if save_res.ok:
                        st.success("Đã thêm mẫu vào Dataset huấn luyện thành công!")
                        st.rerun()
                    else:
                        st.error(f"Thêm thất bại: {save_res.text}")
                except Exception as exc:
                    st.error(f"Lỗi: {exc}")

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

    # List datasets
    st.markdown("<h3>📋 Danh sách mẫu dữ liệu</h3>", unsafe_allow_html=True)
    try:
        list_res = requests.get(api_url("/api/admin/dataset"), headers=auth_headers(), timeout=20)
        datasets = list_res.json() if list_res.ok else []
    except Exception as exc:
        st.error(f"Lỗi tải danh sách mẫu dữ liệu: {exc}")
        datasets = []

    if not datasets:
        st.info("Chưa có mẫu dữ liệu nào trong Dataset.")
        return

    # Render as table or neat cards
    for d in datasets:
        with st.container(border=True, key=f"ds_item_{d['id']}"):
            st.markdown(f"<b>Mẫu #{d['id']}</b> | Video ID: {d['video_id']} | Ngày tạo: {d['created_at'][:16].replace('T', ' ')}", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background: rgba(255, 255, 255, 0.02); padding: 0.8rem; border-radius: 8px; border: 1px solid var(--card-border); margin-top: 0.5rem;">
                {d['caption_text']}
            </div>
            """, unsafe_allow_html=True)
