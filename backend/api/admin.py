from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.video import Video
from models.caption_review import CaptionReview
from models.training_job import TrainingJob
from models.model_version import ModelVersion
from core.security import get_current_user
from schemas import UserOut, VideoOut

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    total_users = db.query(User).count()
    total_videos = db.query(Video).count()
    
    pending_reviews = db.query(CaptionReview).filter(CaptionReview.status == "pending").count()
    approved_reviews = db.query(CaptionReview).filter(CaptionReview.status == "approved").count()
    rejected_reviews = db.query(CaptionReview).filter(CaptionReview.status == "rejected").count()
    
    total_jobs = db.query(TrainingJob).count()
    active_model = db.query(ModelVersion).filter(ModelVersion.status == "current").first()
    active_model_ver = active_model.version if active_model else "N/A"
    
    return {
        "total_users": total_users,
        "total_videos": total_videos,
        "caption_reviews": {
            "pending": pending_reviews,
            "approved": approved_reviews,
            "rejected": rejected_reviews,
        },
        "total_training_jobs": total_jobs,
        "active_model_version": active_model_ver
    }

@router.get("/users", response_model=list[UserOut])
def get_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(User).all()

@router.get("/videos", response_model=list[VideoOut])
def get_videos(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    results = db.query(Video, User.name)\
        .outerjoin(User, Video.user_id == User.id)\
        .all()
    
    videos = []
    for video, author_name in results:
        video.author_name = author_name
        videos.append(video)
    return videos

@router.post("/users/{id}/role", response_model=UserOut)
def update_user_role(id: int, role: str = Body(..., embed=True), db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
        
    user.role = role
    db.commit()
    db.refresh(user)
    return user
