import uuid
from sqlalchemy import Column, String, DateTime, JSON
from app.database.base import Base, utc_now

class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(100), nullable=False, index=True)  # hardware_connect, sensor_reading, alert_triggered, rag_query, stt_transcription
    source = Column(String(100), nullable=False)
    details_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
