from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Video Social App"
    database_url: str = "sqlite:///./video_social.db"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    upload_dir: str = "uploads"
    video2text_url: str = "http://127.0.0.1:8001"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
