from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from datetime import datetime
from database.session import get_db
from models.user import User
from models.caption_review import CaptionReview
from models.training_dataset import TrainingDataset
from models.video import Video
from core.security import get_current_user
from schemas import CaptionReviewOut

router = APIRouter(prefix="/admin", tags=["moderation"])

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

@router.get("/caption-reviews", response_model=list[CaptionReviewOut])
def get_caption_reviews(status: str | None = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    query = db.query(CaptionReview)
    if status:
        query = query.filter(CaptionReview.status == status)
    return query.all()

@router.post("/caption-reviews/{id}/approve", response_model=CaptionReviewOut)
def approve_caption_review(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    review = db.query(CaptionReview).filter(CaptionReview.id == id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Caption review not found")
    
    review.status = "approved"
    review.reviewed_by = admin.id
    review.reviewed_at = datetime.utcnow()
    
    # Also update the main Video's caption
    video = db.query(Video).filter(Video.id == review.video_id).first()
    if video:
        video.caption = review.corrected_caption if review.corrected_caption else review.ai_caption
        video.status = "captioned"
        
    # Also check if it exists in training_datasets, if not add it
    dataset_exists = db.query(TrainingDataset).filter(TrainingDataset.caption_review_id == review.id).first()
    if not dataset_exists:
        final_caption = review.corrected_caption if review.corrected_caption else review.ai_caption
        td = TrainingDataset(
            video_id=review.video_id,
            caption_review_id=review.id,
            caption_text=final_caption,
            status="active"
        )
        db.add(td)
        
    db.commit()
    db.refresh(review)
    return review

@router.post("/caption-reviews/{id}/reject", response_model=CaptionReviewOut)
def reject_caption_review(id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    review = db.query(CaptionReview).filter(CaptionReview.id == id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Caption review not found")
    
    review.status = "rejected"
    review.reviewed_by = admin.id
    review.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    return review

@router.post("/caption-reviews/{id}/edit", response_model=CaptionReviewOut)
def edit_caption_review(
    id: int, 
    corrected_caption: str = Body(..., embed=True), 
    db: Session = Depends(get_db), 
    admin: User = Depends(require_admin)
):
    review = db.query(CaptionReview).filter(CaptionReview.id == id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Caption review not found")
    
    review.corrected_caption = corrected_caption
    review.status = "approved"  # Setting to approved automatically when edited
    review.reviewed_by = admin.id
    review.reviewed_at = datetime.utcnow()
    
    # Also update the main Video's caption
    video = db.query(Video).filter(Video.id == review.video_id).first()
    if video:
        video.caption = corrected_caption
        video.status = "captioned"
        
    # Also check if it exists in training_datasets, if not add it
    dataset_exists = db.query(TrainingDataset).filter(TrainingDataset.caption_review_id == review.id).first()
    if not dataset_exists:
        td = TrainingDataset(
            video_id=review.video_id,
            caption_review_id=review.id,
            caption_text=corrected_caption,
            status="active"
        )
        db.add(td)
    else:
        dataset_exists.caption_text = corrected_caption
        
    db.commit()
    db.refresh(review)
    return review
