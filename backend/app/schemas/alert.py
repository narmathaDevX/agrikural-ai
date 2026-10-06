from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AlertBase(BaseModel):
    device_id: str
    sensor_id: Optional[str] = None
    sensor_type: str
    severity: str = "warning"  # warning, critical, info
    title: str
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: str
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AlertResolve(BaseModel):
    is_resolved: bool = True
