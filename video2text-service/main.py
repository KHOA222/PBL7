from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from model.caption_engine import get_caption_engine

app = FastAPI(title="Video2Text Service")
engine = get_caption_engine()

class VideoToTextRequest(BaseModel):
    video_path: str

class VideoToTextResponse(BaseModel):
    caption: str
    model_name: str
    processing_time: float
    is_mock: bool = False

@app.get("/")
def root():
    return {"message": "Video2Text service is running", "engine": engine.__class__.__name__}

@app.post("/video-to-text", response_model=VideoToTextResponse)
def video_to_text(payload: VideoToTextRequest):
    try:
        return engine.generate(payload.video_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
