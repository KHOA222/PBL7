from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database.session import Base

class TrainingDataset(Base):
    __tablename__ = "training_datasets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"))
    caption_review_id: Mapped[int | None] = mapped_column(ForeignKey("caption_reviews.id"), nullable=True)
    caption_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
