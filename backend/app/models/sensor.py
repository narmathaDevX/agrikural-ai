from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base, utc_now

class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(String(100), primary_key=True)  # e.g., AGRI-DEV-001-SOIL-1
    device_id = Column(String(100), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    sensor_type = Column(String(100), nullable=False, index=True)  # soil_moisture, temperature, humidity, light, water_level, soil_ph, npk
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)  # %, °C, lux, pH, mg/kg
    min_threshold = Column(Float, nullable=True)  # Warning below this
    max_threshold = Column(Float, nullable=True)  # Warning above this
    critical_min = Column(Float, nullable=True)   # Critical alert below this
    critical_max = Column(Float, nullable=True)   # Critical alert above this
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    device = relationship("Device", back_populates="sensors")
