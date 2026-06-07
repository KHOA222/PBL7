import unittest
import os
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set up environment path to import modules from backend
import sys
sys.path.insert(0, os.path.dirname(__file__))

from main import app
from database.session import Base, get_db
from core.security import hash_password, verify_password
from models.user import User
from models.video import Video
from models.comment import Comment
from models.caption_review import CaptionReview
from models.training_dataset import TrainingDataset
from models.training_job import TrainingJob
from models.model_version import ModelVersion

# Setup test database
TEST_DATABASE_URL = "sqlite:///./test_video_social.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Overwrite SessionLocal and engine at module level to catch all dynamic imports (e.g. background tasks)
import database.session
database.session.SessionLocal = TestingSessionLocal
database.session.engine = test_engine

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Apply dependency override
app.dependency_overrides[get_db] = override_get_db

class TestVideoSocialApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=test_engine)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=test_engine)
        if os.path.exists("./test_video_social.db"):
            try:
                os.remove("./test_video_social.db")
            except Exception:
                pass

    def setUp(self):
        # Clear tables before each test to ensure test isolation
        db = TestingSessionLocal()
        db.query(Comment).delete()
        db.query(TrainingDataset).delete()
        db.query(TrainingJob).delete()
        db.query(ModelVersion).delete()
        db.query(CaptionReview).delete()
        db.query(Video).delete()
        db.query(User).delete()
        db.commit()
        db.close()

    def _create_user(self, name, email, password, role="user"):
        db = TestingSessionLocal()
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user

    def test_auth_register_and_login_sanitization(self):
        # 1. Test Registration
        register_payload = {
            "name": "Test User",
            "email": "Test_User@Example.Com",  # Mixed case
            "password": "mypassword"
        }
        res = self.client.post("/api/auth/register", json=register_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["email"], "test_user@example.com")

        # 2. Test Login Casing & Whitespace Sanitization (our implemented feature)
        # Login with lowercase email and trailing spaces
        login_data = {
            "username": "  test_user@example.com  ",  # lowercase + spaces
            "password": "mypassword"
        }
        res_login = self.client.post("/api/auth/login", data=login_data)
        self.assertEqual(res_login.status_code, 200)
        login_res_json = res_login.json()
        self.assertIn("access_token", login_res_json)
        self.assertEqual(login_res_json["user"]["name"], "Test User")

        # Login with wrong password
        login_wrong_pwd = {
            "username": "test_user@example.com",
            "password": "wrongpassword"
        }
        res_fail = self.client.post("/api/auth/login", data=login_wrong_pwd)
        self.assertEqual(res_fail.status_code, 401)

    def test_admin_role_protection_and_modification(self):
        # Create normal user and admin
        self._create_user("Normal User", "user@mail.com", "password", "user")
        self._create_user("Admin User", "admin@mail.com", "1", "admin")

        # Get tokens
        user_token = self.client.post("/api/auth/login", data={"username": "user@mail.com", "password": "password"}).json()["access_token"]
        admin_token = self.client.post("/api/auth/login", data={"username": "admin@mail.com", "password": "1"}).json()["access_token"]

        # Fetch stats as normal user -> Should fail with 403
        res_stats_user = self.client.get("/api/admin/stats", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(res_stats_user.status_code, 403)

        # Fetch stats as admin -> Should succeed
        res_stats_admin = self.client.get("/api/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res_stats_admin.status_code, 200)
        self.assertIn("total_users", res_stats_admin.json())

        # Change user role to admin as admin
        target_user = TestingSessionLocal().query(User).filter(User.email == "user@mail.com").first()
        res_role = self.client.post(
            f"/api/admin/users/{target_user.id}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(res_role.status_code, 200)
        self.assertEqual(res_role.json()["role"], "admin")

    def test_videos_join_query_and_comments_batch_fetching(self):
        # Create normal user & admin
        user = self._create_user("Bob", "bob@mail.com", "password", "user")
        admin = self._create_user("Admin", "admin@mail.com", "1", "admin")
        
        user_token = self.client.post("/api/auth/login", data={"username": "bob@mail.com", "password": "password"}).json()["access_token"]
        admin_token = self.client.post("/api/auth/login", data={"username": "admin@mail.com", "password": "1"}).json()["access_token"]

        # Create dummy video file
        dummy_file_path = "test_video.mp4"
        with open(dummy_file_path, "wb") as f:
            f.write(b"dummy mp4 data")

        # Upload Video
        with open(dummy_file_path, "rb") as f:
            res_upload = self.client.post(
                "/api/videos/upload",
                data={"title": "Test Video", "description": "Desc", "hashtags": "#test"},
                files={"file": ("test_video.mp4", f, "video/mp4")},
                headers={"Authorization": f"Bearer {user_token}"}
            )
        
        # Cleanup dummy file
        if os.path.exists(dummy_file_path):
            os.remove(dummy_file_path)

        self.assertEqual(res_upload.status_code, 200)
        video_id = res_upload.json()["id"]

        # Verify that listing videos correctly populates author_name via JOIN (optimized query)
        res_list = self.client.get("/api/videos")
        self.assertEqual(res_list.status_code, 200)
        videos = res_list.json()
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["author_name"], "Bob")  # Author name populated correctly
        self.assertEqual(videos[0]["id"], video_id)

        # Test Comments Batch Fetching (our optimized endpoint)
        # 1. Fetch all comments (expect empty)
        res_all_comments_empty = self.client.get("/api/comments")
        self.assertEqual(res_all_comments_empty.status_code, 200)
        self.assertEqual(len(res_all_comments_empty.json()), 0)

        # 2. Add comment
        res_comment = self.client.post(
            f"/api/comments/video/{video_id}",
            json={"content": "Great video!"},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        self.assertEqual(res_comment.status_code, 200)

        # 3. Fetch all comments (expecting 1 comment in batch)
        res_all_comments = self.client.get("/api/comments")
        self.assertEqual(res_all_comments.status_code, 200)
        all_comments = res_all_comments.json()
        self.assertEqual(len(all_comments), 1)
        self.assertEqual(all_comments[0]["content"], "Great video!")
        self.assertEqual(all_comments[0]["video_id"], video_id)
        self.assertEqual(all_comments[0]["user_id"], user.id)

    @patch("api.videos.generate_caption")
    def test_caption_review_approval_moderation_dataset_sync(self, mock_generate_caption):
        # Setup mock caption response
        mock_generate_caption.return_value = {
            "caption": "A beautiful sunset in beach",
            "model_name": "Video-Captioner-v1.0",
            "processing_time": 2.4
        }

        # Create user and admin
        user = self._create_user("Bob", "bob@mail.com", "password", "user")
        admin = self._create_user("Admin", "admin@mail.com", "1", "admin")
        
        user_token = self.client.post("/api/auth/login", data={"username": "bob@mail.com", "password": "password"}).json()["access_token"]
        admin_token = self.client.post("/api/auth/login", data={"username": "admin@mail.com", "password": "1"}).json()["access_token"]

        # Insert video into DB directly for simpler test flow
        db = TestingSessionLocal()
        video = Video(
            user_id=user.id,
            title="Sunrise",
            video_url="/api/videos/file/sunrise.mp4",
            file_path="sunrise.mp4",
            status="uploaded"
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        video_id = video.id
        db.close()

        # Trigger AI caption generation
        res_caption = self.client.post(
            f"/api/videos/{video_id}/caption",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        self.assertEqual(res_caption.status_code, 200)
        self.assertEqual(res_caption.json()["status"], "captioned")
        self.assertEqual(res_caption.json()["caption"], "A beautiful sunset in beach")

        # Verify that a pending CaptionReview was created in the database
        res_reviews = self.client.get(
            "/api/admin/caption-reviews?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(res_reviews.status_code, 200)
        reviews_list = res_reviews.json()
        self.assertEqual(len(reviews_list), 1)
        review_id = reviews_list[0]["id"]
        self.assertEqual(reviews_list[0]["ai_caption"], "A beautiful sunset in beach")

        # Edit and Approve the caption review as Admin
        res_moderation = self.client.post(
            f"/api/admin/caption-reviews/{review_id}/edit",
            json={"corrected_caption": "Bình minh tuyệt đẹp trên bãi biển xanh cát vàng"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(res_moderation.status_code, 200)
        self.assertEqual(res_moderation.json()["status"], "approved")
        self.assertEqual(res_moderation.json()["corrected_caption"], "Bình minh tuyệt đẹp trên bãi biển xanh cát vàng")

        # Verify the Video's caption in the database was updated to the corrected caption
        db = TestingSessionLocal()
        updated_video = db.query(Video).filter(Video.id == video_id).first()
        self.assertEqual(updated_video.caption, "Bình minh tuyệt đẹp trên bãi biển xanh cát vàng")
        self.assertEqual(updated_video.status, "captioned")

        # Verify a record was automatically pushed to training dataset (TrainingDataset)
        dataset_sample = db.query(TrainingDataset).filter(TrainingDataset.caption_review_id == review_id).first()
        self.assertIsNotNone(dataset_sample)
        self.assertEqual(dataset_sample.caption_text, "Bình minh tuyệt đẹp trên bãi biển xanh cát vàng")
        self.assertEqual(dataset_sample.status, "active")
        db.close()

    @patch("time.sleep", return_value=None)
    def test_training_jobs_and_model_versioning(self, mock_sleep):
        admin = self._create_user("Admin", "admin@mail.com", "1", "admin")
        admin_token = self.client.post("/api/auth/login", data={"username": "admin@mail.com", "password": "1"}).json()["access_token"]

        # Insert some active training dataset records
        db = TestingSessionLocal()
        td1 = TrainingDataset(video_id=1, caption_text="Mẫu tập huấn 1", status="active")
        td2 = TrainingDataset(video_id=2, caption_text="Mẫu tập huấn 2", status="active")
        db.add_all([td1, td2])
        db.commit()
        db.close()

        # 1. Create a training job
        job_payload = {
            "model_name": "VideoCaptioner-MSRVTT-Pro",
            "config_json": json.dumps({"learning_rate": 0.0001, "epochs": 20, "batch_size": 32})
        }
        res_job_create = self.client.post(
            "/api/admin/training/jobs",
            json=job_payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(res_job_create.status_code, 200)
        job_data = res_job_create.json()
        self.assertEqual(job_data["status"], "pending")
        self.assertEqual(job_data["dataset_size"], 2)
        job_id = job_data["id"]

        # 2. Start the training job
        # Note: TestClient runs background tasks synchronously. This means when we hit /start,
        # it calls the endpoint AND runs the simulate_training_run task immediately before returning the response.
        res_job_start = self.client.post(
            f"/api/admin/training/jobs/{job_id}/start",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        self.assertEqual(res_job_start.status_code, 200)
        
        # Verify database state after background execution completes (completed synchronously by TestClient)
        db = TestingSessionLocal()
        finished_job = db.query(TrainingJob).filter(TrainingJob.id == job_id).first()
        self.assertEqual(finished_job.status, "completed")
        self.assertIsNotNone(finished_job.result_metrics_json)
        
        metrics = json.loads(finished_job.result_metrics_json)
        self.assertIn("bleu_4", metrics)
        self.assertIn("cider", metrics)
        self.assertIn("loss", metrics)

        # 3. Verify a new candidate Model Version was automatically generated
        candidate_version = db.query(ModelVersion).filter(ModelVersion.version == f"v1.0.{job_id}").first()
        self.assertIsNotNone(candidate_version)
        self.assertEqual(candidate_version.status, "candidate")
        self.assertEqual(candidate_version.checkpoint_path, f"/models/checkpoints/VideoCaptioner-MSRVTT-Pro_v1.0.{job_id}")
        db.close()

if __name__ == "__main__":
    unittest.main()
