import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agrikural AI System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/agrikural.db",
        description="PostgreSQL URL (e.g. postgresql+asyncpg://postgres:postgres@localhost:5432/agrikural) or SQLite fallback"
    )
    SQL_ECHO: bool = False

    # Security & Auth
    JWT_SECRET: str = "agrikural-super-secret-key-change-in-production-2026-secure"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ChromaDB Vector Store
    CHROMA_PATH: str = "./data/chroma_db"
    CHROMA_COLLECTION: str = "agriculture_knowledge"
    TOP_K: int = 5

    # Embeddings
    EMBEDDING_PROVIDER: str = "local"  # local, sentence_transformers, huggingface
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # LLM Reasoning
    LLM_PROVIDER: str = "local"  # local, ollama, openai, gemini, huggingface
    LLM_MODEL: str = "agrikural-reasoner-v1"
    LLM_API_BASE: str = "http://localhost:11434/v1"
    LLM_API_KEY: str = ""

    # Speech-to-Text (STT)
    STT_PROVIDER: str = "local"  # local, whisper, hf
    STT_MODEL: str = "whisper-base-multilingual"

    # Translation
    TRANSLATION_PROVIDER: str = "local"  # local, marian, indictrans, hf
    TRANSLATION_MODEL: str = "indic-trans-multilingual"

    # Text-to-Speech (TTS)
    TTS_PROVIDER: str = "gtts"  # gtts, local, edge_tts
    TTS_MODEL: str = "indic-tts"

    # Storage & Uploads
    UPLOAD_DIR: str = "./data/uploads"
    AUDIO_DIR: str = "./data/audio"

    # Hardware & Gateway
    SIMULATOR_INTERVAL_SECONDS: float = 3.0
    GATEWAY_SECRET: str = "agrikural-hardware-gateway-secret-token"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
os.makedirs(settings.CHROMA_PATH, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
os.makedirs("./data", exist_ok=True)
