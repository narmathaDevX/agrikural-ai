import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base, utc_now

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="farmer", nullable=False)  # admin, farmer, viewer
    preferred_language = Column(String(10), default="ta", nullable=False)  # ta, ml, en
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
