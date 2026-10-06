import uuid
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.base import Base, utc_now

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(100), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    sensor_id = Column(String(100), nullable=True)
    sensor_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="warning", nullable=False)  # warning, critical, info
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    device = relationship("Device", back_populates="alerts")
