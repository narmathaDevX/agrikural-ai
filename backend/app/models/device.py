from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from app.database.base import Base, utc_now

class Device(Base):
    __tablename__ = "devices"

    id = Column(String(100), primary_key=True)  # e.g., AGRI-DEV-001
    name = Column(String(255), nullable=False)
    farm_name = Column(String(255), default="Kural Organic Farm")
    location = Column(String(255), default="Coimbatore, Tamil Nadu")
    crop_type = Column(String(100), default="Tomato")
    status = Column(String(50), default="online")  # online, offline, warning, maintenance
    last_seen = Column(DateTime, default=utc_now)
    ip_address = Column(String(50), default="192.168.1.100")
    firmware_version = Column(String(50), default="v2.4.1")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    sensors = relationship("Sensor", back_populates="device", cascade="all, delete-orphan", lazy="selectin")
    readings = relationship("SensorReading", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")
