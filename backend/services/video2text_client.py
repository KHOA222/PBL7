import httpx
from core.config import settings

async def generate_caption(video_path: str) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{settings.video2text_url}/video-to-text", json={"video_path": video_path})
        resp.raise_for_status()
        return resp.json()
