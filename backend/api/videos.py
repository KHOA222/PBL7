from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database.session import get_db
from core.config import settings
from core.security import get_current_user
from models.user import User
from models.video import Video
from models.caption_job import CaptionJob
from models.caption_review import CaptionReview
from schemas import VideoOut
from services.video2text_client import generate_caption

router = APIRouter(prefix="/videos", tags=["videos"])

def _attach_author(video: Video, db: Session) -> Video:
    user = db.query(User.name).filter(User.id == video.user_id).first()
    video.author_name = user[0] if user else None
    return video

@router.get("", response_model=list[VideoOut])
def list_videos(db: Session = Depends(get_db)):
    results = db.query(Video, User.name)\
        .outerjoin(User, Video.user_id == User.id)\
        .filter(Video.status != "caption_failed")\
        .order_by(Video.created_at.desc()).all()
    
    videos = []
    for video, author_name in results:
        video.author_name = author_name
        videos.append(video)
    return videos

@router.post("/upload", response_model=VideoOut)
async def upload_video(
    title: str = Form(...),
    description: str = Form(""),
    hashtags: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    filename = f"{uuid4().hex}{ext}"
    path = upload_dir / filename
    path.write_bytes(await file.read())

    video = Video(
        user_id=user.id,
        title=title,
        description=description,
        hashtags=hashtags,
        file_path=str(path),
        video_url=f"/api/videos/file/{filename}",
        status="uploaded",
    )
    db.add(video); db.commit(); db.refresh(video)
    return video

@router.post("/{video_id}/caption", response_model=VideoOut)
async def create_caption(video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    video.status = "processing"
    job = CaptionJob(video_id=video.id, status="processing")
    db.add(job); db.commit()
    try:
        result = await generate_caption(video.file_path)
        video.caption = result.get("caption")
        video.status = "captioned"
        job.status = "done"
        job.result = video.caption
        job.model_name = result.get("model_name")
        job.processing_time = result.get("processing_time")
        existing = db.query(CaptionReview).filter(CaptionReview.video_id == video.id).first()
        if not existing:
            db.add(CaptionReview(video_id=video.id, ai_caption=video.caption, status="pending"))
    except Exception as exc:
        video.status = "caption_failed"
        job.status = "failed"
        job.result = str(exc)
    db.commit(); db.refresh(video)
    return video

@router.get("/file/{filename}")
@router.get("/stream/{filename}")
def get_video_file(filename: str):
    path = Path(settings.upload_dir) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)

@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return _attach_author(video, db)

from pydantic import BaseModel

class VideoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    hashtags: str | None = None

@router.patch("/{video_id}", response_model=VideoOut)
def update_video(video_id: int, payload: VideoUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == user.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if payload.title is not None:
        video.title = payload.title
    if payload.description is not None:
        video.description = payload.description
    if payload.hashtags is not None:
        video.hashtags = payload.hashtags
    db.commit(); db.refresh(video)
    return _attach_author(video, db)

@router.delete("/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == user.id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    Path(video.file_path).unlink(missing_ok=True)
    db.delete(video); db.commit()
    return {"ok": True}
