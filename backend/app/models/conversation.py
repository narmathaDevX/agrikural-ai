import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base, utc_now

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    device_id = Column(String(100), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), default="Agricultural Consultation")
    language = Column(String(10), default="ta")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    original_text = Column(Text, nullable=False)
    detected_language = Column(String(10), default="en", nullable=False)
    translated_english_text = Column(Text, nullable=True)
    translated_output_text = Column(Text, nullable=True)
    audio_url = Column(String(500), nullable=True)
    retrieved_documents_json = Column(JSON, default=list, nullable=True)
    sensor_context_json = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
