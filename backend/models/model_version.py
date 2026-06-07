from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database.session import Base

class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    version: Mapped[str] = mapped_column(String(50))
    checkpoint_path: Mapped[str] = mapped_column(String(500))
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="candidate")  # current / candidate / archived
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
