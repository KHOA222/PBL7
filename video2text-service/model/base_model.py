from abc import ABC, abstractmethod

class BaseVideoCaptionModel(ABC):
    @abstractmethod
    def generate(self, video_path: str) -> dict:
        """Return dict: caption, model_name, processing_time."""
        raise NotImplementedError
