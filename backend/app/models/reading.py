from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base, utc_now

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(100), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    sensor_id = Column(String(100), nullable=False, index=True)
    sensor_type = Column(String(100), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    location = Column(String(255), nullable=True)
    metadata_json = Column(JSON, default=dict)

    device = relationship("Device", back_populates="readings")
