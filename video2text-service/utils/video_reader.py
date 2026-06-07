from pathlib import Path
import cv2


def read_video_stats(video_path: str) -> dict:
    path = Path(video_path)
    if not path.exists():
        return {"exists": False, "frames": 0, "fps": 0.0, "duration": 0.0}
    cap = cv2.VideoCapture(str(path))
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    cap.release()
    duration = frames / fps if fps > 0 else 0.0
    return {"exists": True, "frames": frames, "fps": fps, "duration": duration}
