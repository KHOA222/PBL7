from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database.session import Base

class CaptionJob(Base):
    __tablename__ = "caption_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
