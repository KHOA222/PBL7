from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.session import get_db
from core.security import get_current_user
from models.user import User
from models.video import Video
from models.comment import Comment
from schemas import CommentCreate, CommentOut

router = APIRouter(prefix="/comments", tags=["comments"])

@router.get("", response_model=list[CommentOut])
def list_all_comments(db: Session = Depends(get_db)):
    return db.query(Comment).order_by(Comment.created_at.asc()).all()

@router.get("/video/{video_id}", response_model=list[CommentOut])
def list_comments(video_id: int, db: Session = Depends(get_db)):
    return db.query(Comment).filter(Comment.video_id == video_id).order_by(Comment.created_at.asc()).all()

@router.post("/video/{video_id}", response_model=CommentOut)
def create_comment(video_id: int, payload: CommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    comment = Comment(video_id=video_id, user_id=user.id, content=payload.content)
    db.add(comment); db.commit(); db.refresh(comment)
    return comment
