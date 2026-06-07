from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database.session import Base

class TrainingJob(Base):
    __tablename__ = "training_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="pending")  # pending / running / evaluating / completed / failed
    dataset_size: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
