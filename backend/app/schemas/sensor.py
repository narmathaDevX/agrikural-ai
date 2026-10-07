from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class SensorBase(BaseModel):
    id: str
    sensor_type: str
    name: str
    unit: str
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    critical_min: Optional[float] = None
    critical_max: Optional[float] = None
    is_active: bool = True

class SensorCreate(SensorBase):
    device_id: str

class SensorResponse(SensorBase):
    device_id: str
    created_at: datetime
    current_value: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class SensorReadingCreate(BaseModel):
    device_id: str
    sensor_id: Optional[str] = None
    sensor_type: str
    value: float
    unit: str
    timestamp: Optional[datetime] = None
    location: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class BatchSensorReadings(BaseModel):
    device_id: str
    readings: List[SensorReadingCreate]

class SensorReadingResponse(BaseModel):
    id: int
    device_id: str
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime
    location: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
