from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
from models.training_dataset import TrainingDataset
from models.video import Video
from core.security import get_current_user
from schemas import TrainingDatasetOut

router = APIRouter(prefix="/admin/dataset", tags=["dataset"])

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

@router.get("", response_model=list[TrainingDatasetOut])
def get_datasets(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(TrainingDataset).all()

@router.get("/stats")
def get_dataset_stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    total_samples = db.query(TrainingDataset).count()
    active_samples = db.query(TrainingDataset).filter(TrainingDataset.status == "active").count()
    return {
        "total_samples": total_samples,
        "active_samples": active_samples
    }

@router.post("/add-approved-caption", response_model=TrainingDatasetOut)
def add_approved_caption(
    video_id: int = Body(..., embed=True),
    caption_text: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    td = TrainingDataset(
        video_id=video_id,
        caption_review_id=None,  # Manually added, no review needed
        caption_text=caption_text,
        status="active"
    )
    db.add(td)
    db.commit()
    db.refresh(td)
    return td
