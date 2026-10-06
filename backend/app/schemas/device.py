from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.sensor import SensorResponse

class DeviceBase(BaseModel):
    id: str  # e.g. AGRI-DEV-001
    name: str
    farm_name: Optional[str] = "Kural Organic Farm"
    location: Optional[str] = "Coimbatore, Tamil Nadu"
    crop_type: Optional[str] = "Tomato"
    status: Optional[str] = "online"
    ip_address: Optional[str] = "192.168.1.100"
    firmware_version: Optional[str] = "v2.4.1"
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    farm_name: Optional[str] = None
    location: Optional[str] = None
    crop_type: Optional[str] = None
    status: Optional[str] = None
    ip_address: Optional[str] = None
    firmware_version: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

class DeviceResponse(DeviceBase):
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sensors: List[SensorResponse] = []
    latest_readings: Optional[Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
