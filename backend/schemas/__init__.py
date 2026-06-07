from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    class Config:
        from_attributes = True

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class VideoOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None = None
    hashtags: str | None = None
    video_url: str
    caption: str | None = None
    status: str
    created_at: datetime
    author_name: str | None = None
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str

class CommentOut(BaseModel):
    id: int
    video_id: int
    user_id: int
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

class CaptionReviewOut(BaseModel):
    id: int
    video_id: int
    ai_caption: str
    corrected_caption: str | None = None
    status: str
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    class Config:
        from_attributes = True

class TrainingDatasetOut(BaseModel):
    id: int
    video_id: int
    caption_review_id: int | None = None
    caption_text: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True

class TrainingJobCreate(BaseModel):
    model_name: str
    config_json: str | None = None

class TrainingJobOut(BaseModel):
    id: int
    model_name: str
    status: str
    dataset_size: int
    config_json: str | None = None
    result_metrics_json: str | None = None
    created_by: int
    created_at: datetime
    class Config:
        from_attributes = True

class ModelVersionOut(BaseModel):
    id: int
    version: str
    checkpoint_path: str
    metrics_json: str | None = None
    status: str
    deployed_at: datetime | None = None
    class Config:
        from_attributes = True
