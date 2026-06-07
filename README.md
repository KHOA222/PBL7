# Video Social App MVP

MVP gồm 3 service:

- `backend`: FastAPI API chính
- `frontend`: Streamlit UI
- `video2text-service`: FastAPI service sinh caption từ video

## Chạy nhanh local

### 1. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Video2Text service
```bash
cd video2text-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Nếu chưa có checkpoint, service sẽ chạy `MockCaptionEngine` để demo.

### 3. Frontend
```bash
cd frontend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Tài khoản đầu tiên có thể đăng ký trực tiếp ở trang Login.
