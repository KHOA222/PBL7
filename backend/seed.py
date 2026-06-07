"""Seed 3 users (including 1 admin) + sample videos and admin flow data into the database."""
import os, sys
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))

from database.session import Base, engine, SessionLocal
from models.user import User
from models.video import Video
from models.caption_review import CaptionReview
from models.training_dataset import TrainingDataset
from models.training_job import TrainingJob
from models.model_version import ModelVersion
from core.security import hash_password

UPLOAD_DIR = "uploads"

USERS = [
    {"name": "Alice", "email": "alice@example.com", "password": "password123", "role": "user"},
    {"name": "Bob",   "email": "bob@example.com",   "password": "password123", "role": "user"},
    {"name": "Admin", "email": "admin@mail.com", "password": "1", "role": "admin"},
]

VIDEOS = [
    {"title": "Mèo chơi đùa",       "description": "Clip hài hước về mèo",        "hashtags": "#meo #cute",      "caption": "A cat is playing with a ball of yarn"},
    {"title": "Hoàng hôn biển",      "description": "Cảnh hoàng hôn tuyệt đẹp",    "hashtags": "#sunset #bien",   "caption": "The sun sets over the ocean horizon"},
    {"title": "Nấu phở bò",          "description": "Hướng dẫn nấu phở truyền thống","hashtags": "#cooking #pho",  "caption": "A person is cooking beef noodle soup"},
    {"title": "Chạy marathon",        "description": "Khoảnh khắc về đích",         "hashtags": "#sport #run",     "caption": "Runners crossing the marathon finish line"},
    {"title": "Du lịch Đà Lạt",      "description": "Vlog một ngày ở Đà Lạt",      "hashtags": "#travel #dalat",  "caption": "A person explores a misty mountain town"},
    {"title": "Học guitar acoustic",  "description": "Tutorial hợp âm cơ bản",      "hashtags": "#music #guitar",  "caption": "Hands playing chords on an acoustic guitar"},
    {"title": "Thác Bản Giốc",        "description": "Cảnh thác nước hùng vĩ",      "hashtags": "#nature #waterfall","caption": "A large waterfall surrounded by green forest"},
    {"title": "Đua xe đạp địa hình",  "description": "MTB trail Tà Xùa",            "hashtags": "#sport #mtb",     "caption": "A cyclist rides down a mountain trail"},
    {"title": "Cà phê sáng Hà Nội",   "description": "V văn hóa cà phê trứng",       "hashtags": "#food #coffee",   "caption": "A cup of egg coffee on a wooden table"},
    {"title": "Pháo hoa Tết 2025",    "description": "Khoảnh khắc giao thừa",       "hashtags": "#tet #fireworks", "caption": "Colorful fireworks light up the night sky"},
]

def main():
    Base.metadata.create_all(bind=engine)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db = SessionLocal()

    # Create users
    user_objs = []
    for u in USERS:
        user = db.query(User).filter(User.email == u["email"]).first()
        if not user:
            user = User(
                name=u["name"], 
                email=u["email"], 
                password_hash=hash_password(u["password"]),
                role=u["role"]
            )
            db.add(user)
            db.flush()
            print(f"Created user: {u['email']} (role: {u['role']})")
        else:
            print(f"User exists: {u['email']}")
        user_objs.append(user)
    db.commit()
    for u in user_objs:
        db.refresh(u)

    # Create videos
    video_objs = []
    for i, v in enumerate(VIDEOS):
        owner = user_objs[i % len(user_objs)]
        filename = f"sample_video_{i+1:02d}.mp4"
        file_path = os.path.abspath(os.path.join(UPLOAD_DIR, filename))

        # Create a minimal valid-looking placeholder file
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(b"\x00" * 1024)  # 1 KB placeholder

        video = db.query(Video).filter(Video.file_path == file_path).first()
        if not video:
            video = Video(
                user_id=owner.id,
                title=v["title"],
                description=v["description"],
                hashtags=v["hashtags"],
                video_url=f"/api/videos/stream/{filename}",
                file_path=file_path,
                caption=v["caption"],
                status="captioned",
            )
            db.add(video)
            db.flush()
            print(f"Created video: {v['title']}")
        else:
            print(f"Video exists: {v['title']}")
        video_objs.append(video)

    db.commit()
    for v in video_objs:
        db.refresh(v)

    # Seed Admin Flow Data
    print("Seeding admin flow mock data...")
    admin_user = next(u for u in user_objs if u.role == "admin")

    # 1. Caption Reviews
    cr1 = db.query(CaptionReview).filter(CaptionReview.id == 1).first()
    if not cr1 and len(video_objs) >= 3:
        cr1 = CaptionReview(
            video_id=video_objs[0].id,
            ai_caption=video_objs[0].caption,
            corrected_caption=None,
            status="pending"
        )
        cr2 = CaptionReview(
            video_id=video_objs[1].id,
            ai_caption=video_objs[1].caption,
            corrected_caption="Hoàng hôn buông xuống chân trời đại dương bao la màu tím hồng",
            status="approved",
            reviewed_by=admin_user.id,
            reviewed_at=datetime.utcnow()
        )
        cr3 = CaptionReview(
            video_id=video_objs[2].id,
            ai_caption=video_objs[2].caption,
            corrected_caption=None,
            status="rejected",
            reviewed_by=admin_user.id,
            reviewed_at=datetime.utcnow()
        )
        db.add_all([cr1, cr2, cr3])
        db.flush()

    # 2. Training Dataset
    td1 = db.query(TrainingDataset).filter(TrainingDataset.id == 1).first()
    if not td1 and len(video_objs) >= 4:
        td1 = TrainingDataset(
            video_id=video_objs[1].id,
            caption_review_id=2,
            caption_text="Hoàng hôn buông xuống chân trời đại dương bao la màu tím hồng",
            status="active"
        )
        td2 = TrainingDataset(
            video_id=video_objs[3].id,
            caption_review_id=None,
            caption_text="Vận động viên điền kinh vượt qua vạch đích chạy marathon",
            status="active"
        )
        db.add_all([td1, td2])
        db.flush()

    # 3. Training Jobs
    tj1 = db.query(TrainingJob).filter(TrainingJob.id == 1).first()
    if not tj1:
        tj1 = TrainingJob(
            model_name="Video-Captioner-v1.0",
            status="completed",
            dataset_size=12,
            config_json=json.dumps({"learning_rate": 0.001, "epochs": 5, "batch_size": 16}),
            result_metrics_json=json.dumps({"bleu_4": 0.435, "cider": 0.885, "loss": 0.095}),
            created_by=admin_user.id
        )
        tj2 = TrainingJob(
            model_name="Video-Captioner-v2.0",
            status="pending",
            dataset_size=15,
            config_json=json.dumps({"learning_rate": 0.0005, "epochs": 10, "batch_size": 32}),
            created_by=admin_user.id
        )
        db.add_all([tj1, tj2])
        db.flush()

    # 4. Model Versions
    mv1 = db.query(ModelVersion).filter(ModelVersion.id == 1).first()
    if not mv1:
        mv1 = ModelVersion(
            version="v1.0.0",
            checkpoint_path="/models/checkpoints/Video-Captioner-v1.0_v1.0.0",
            metrics_json=json.dumps({"bleu_4": 0.435, "cider": 0.885, "loss": 0.095}),
            status="current",
            deployed_at=datetime.utcnow()
        )
        mv2 = ModelVersion(
            version="v1.0.1",
            checkpoint_path="/models/checkpoints/Video-Captioner-v2.0_v1.0.1",
            metrics_json=json.dumps({"bleu_4": 0.442, "cider": 0.901, "loss": 0.088}),
            status="candidate"
        )
        db.add_all([mv1, mv2])
        db.flush()

    db.commit()
    db.close()
    print("Seed completed successfully.")

if __name__ == "__main__":
    main()
