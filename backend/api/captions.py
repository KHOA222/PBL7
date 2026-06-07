from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from core.security import get_current_user
from models.caption_job import CaptionJob
from models.user import User

router = APIRouter(prefix="/captions", tags=["captions"])

@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(CaptionJob).order_by(CaptionJob.created_at.desc()).all()
