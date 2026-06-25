from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./interview.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    UPLOAD_DIR: str = "./uploads"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    CHROMA_PATH: str = "./chroma_db"
    WHISPER_MODEL: str = "base.en"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    TTS_ENGINE: str = "say"  # say | piper
    PIPER_VOICE_PATH: str = "./voices/en_US-lessac-medium.onnx"
    MAX_INTERVIEW_TURNS: int = 6
    CORS_ORIGINS: str = "http://localhost:5173"  # comma-separated
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
    

settings = get_settings()
