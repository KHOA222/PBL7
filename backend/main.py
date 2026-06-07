from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.session import Base, engine
from models.user import User
from models.video import Video
from models.comment import Comment
from models.caption_job import CaptionJob
from models.caption_review import CaptionReview
from models.training_dataset import TrainingDataset
from models.training_job import TrainingJob
from models.model_version import ModelVersion
from api.auth import router as auth_router
from api.videos import router as videos_router
from api.comments import router as comments_router
from api.users import router as users_router
from api.captions import router as captions_router
from api.admin import router as admin_router
from api.moderation import router as moderation_router
from api.dataset import router as dataset_router
from api.training import router as training_router
from api.model_versions import router as model_versions_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Video Social App API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(videos_router, prefix="/api")
app.include_router(comments_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(captions_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(moderation_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(model_versions_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Video Social App API is running"}
