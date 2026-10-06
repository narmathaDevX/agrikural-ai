from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class SourceCitation(BaseModel):
    title: str
    organization: str
    page: Optional[int] = 1
    section: Optional[str] = "General"
    document_id: str
    relevance_score: float
    crop: Optional[str] = None
    topic: Optional[str] = None
    snippet: Optional[str] = None

class RAGQueryRequest(BaseModel):
    question: str
    language: Optional[str] = None  # None for auto-detect (ta, ml, en)
    device_id: Optional[str] = None  # For combining sensor data
    crop: Optional[str] = None
    region: Optional[str] = None
    topic: Optional[str] = None
    top_k: Optional[int] = 5
    conversation_id: Optional[str] = None

class RAGQueryResponse(BaseModel):
    answer: str
    translated_answer: Optional[str] = None
    original_question: str
    detected_language: str
    translated_question: Optional[str] = None
    sources: List[SourceCitation] = []
    sensor_context: Optional[Dict[str, Any]] = None
    language: str
    confidence_score: float = 0.95
    audio_url: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None

class RAGDebugInfo(BaseModel):
    original_query: str
    detected_language: str
    translated_query: str
    retrieved_chunks: List[Dict[str, Any]]
    sensor_context: Dict[str, Any]
    final_prompt: str
    llm_raw_response: str
    sources: List[SourceCitation]

class DocumentMetadataSchema(BaseModel):
    document_id: str
    title: str
    source: str = "TNAU / ICAR"
    organization: str = "ICAR - Indian Council of Agricultural Research"
    author: Optional[str] = "Agronomy Advisory Division"
    publication_date: Optional[str] = "2024"
    crop: Optional[str] = "General"
    crop_type: Optional[str] = "Horticulture"
    state: Optional[str] = "Tamil Nadu"
    district: Optional[str] = "All"
    region: Optional[str] = "South India"
    soil_type: Optional[str] = "Loamy"
    topic: Optional[str] = "Cultivation & Irrigation"
    language: Optional[str] = "English"
    document_type: Optional[str] = "Advisory"
    url: Optional[str] = None
    version: Optional[str] = "1.0"

class DocumentResponse(DocumentMetadataSchema):
    file_path: Optional[str] = None
    file_size: int = 0
    chunk_count: int = 0
    status: str = "indexed"
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class KnowledgeSearchRequest(BaseModel):
    query: str
    crop: Optional[str] = None
    region: Optional[str] = None
    topic: Optional[str] = None
    top_k: int = 5
