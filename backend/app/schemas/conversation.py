from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.rag import SourceCitation

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    original_text: str
    detected_language: str
    translated_english_text: Optional[str] = None
    translated_output_text: Optional[str] = None
    audio_url: Optional[str] = None
    retrieved_documents_json: Optional[List[Dict[str, Any]]] = None
    sensor_context_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationCreate(BaseModel):
    title: Optional[str] = "Agricultural Consultation"
    device_id: Optional[str] = None
    language: Optional[str] = "ta"

class ConversationResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    title: str
    language: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
