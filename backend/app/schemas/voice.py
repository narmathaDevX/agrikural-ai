from typing import Optional
from pydantic import BaseModel

class STTResponse(BaseModel):
    text: str
    language: str
    confidence: float = 0.95

class TranslationRequest(BaseModel):
    text: str
    source_language: str
    target_language: str

class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str

class TTSRequest(BaseModel):
    text: str
    language: str  # ta, ml, en

class TTSResponse(BaseModel):
    audio_url: str
    language: str
    format: str = "mp3"
