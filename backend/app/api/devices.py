from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.device import Device
from app.models.sensor import Sensor
from app.models.reading import SensorReading
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse
from app.auth.jwt import get_current_user_optional

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.get("", response_model=List[DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Device).options(selectinload(Device.sensors)).order_by(desc(Device.last_seen))
    )
    devices = result.scalars().all()
    
    device_responses = []
    for d in devices:
        # Fetch latest reading for each sensor type
        latest_readings = {}
        for s in d.sensors:
            sub = await db.execute(
                select(SensorReading)
                .where(SensorReading.device_id == d.id, SensorReading.sensor_id == s.id)
                .order_by(desc(SensorReading.timestamp))
                .limit(1)
            )
            r = sub.scalar_one_or_none()
            if r:
                latest_readings[s.sensor_type] = {
                    "value": r.value,
                    "unit": r.unit,
                    "timestamp": r.timestamp.isoformat()
                }

        resp = DeviceResponse.model_validate(d)
        resp.latest_readings = latest_readings
        device_responses.append(resp)

    return device_responses

@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(device_in: DeviceCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Device).where(Device.id == device_in.id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device with ID '{device_in.id}' already exists"
        )

    device = Device(
        id=device_in.id,
        name=device_in.name,
        farm_name=device_in.farm_name,
        location=device_in.location,
        crop_type=device_in.crop_type,
        status=device_in.status or "online",
        ip_address=device_in.ip_address,
        firmware_version=device_in.firmware_version,
        metadata_json=device_in.metadata_json or {},
        last_seen=datetime.now(timezone.utc)
    )
    db.add(device)
    await db.flush()

    # Create default standard sensors for this agricultural device
    default_sensors = [
        {"id": f"{device.id}-SOIL", "sensor_type": "soil_moisture", "name": "Soil Moisture", "unit": "%", "min": 35.0, "max": 75.0, "crit_min": 25.0, "crit_max": 85.0},
        {"id": f"{device.id}-TEMP", "sensor_type": "temperature", "name": "Ambient Temperature", "unit": "°C", "min": 18.0, "max": 34.0, "crit_min": 12.0, "crit_max": 38.0},
        {"id": f"{device.id}-HUMID", "sensor_type": "humidity", "name": "Relative Humidity", "unit": "%", "min": 45.0, "max": 80.0, "crit_min": 30.0, "crit_max": 90.0},
        {"id": f"{device.id}-LIGHT", "sensor_type": "light_lux", "name": "Solar Radiation / Lux", "unit": "lux", "min": 200.0, "max": 1200.0, "crit_min": 100.0, "crit_max": 1500.0},
        {"id": f"{device.id}-WATER", "sensor_type": "water_level_pct", "name": "Irrigation Tank Level", "unit": "%", "min": 30.0, "max": 100.0, "crit_min": 15.0, "crit_max": 100.0},
    ]

    for s_def in default_sensors:
        s = Sensor(
            id=s_def["id"],
            device_id=device.id,
            sensor_type=s_def["sensor_type"],
            name=s_def["name"],
            unit=s_def["unit"],
            min_threshold=s_def["min"],
            max_threshold=s_def["max"],
            critical_min=s_def["crit_min"],
            critical_max=s_def["crit_max"],
            is_active=True
        )
        db.add(s)

    await db.commit()
    await db.refresh(device)
    
    # Reload with sensors
    res = await db.execute(
        select(Device).options(selectinload(Device.sensors)).where(Device.id == device.id)
    )
    full_dev = res.scalar_one()
    return DeviceResponse.model_validate(full_dev)

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Device).options(selectinload(Device.sensors)).where(Device.id == device_id)
    )
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    latest_readings = {}
    for s in device.sensors:
        sub = await db.execute(
            select(SensorReading)
            .where(SensorReading.device_id == device.id, SensorReading.sensor_id == s.id)
            .order_by(desc(SensorReading.timestamp))
            .limit(1)
        )
        r = sub.scalar_one_or_none()
        if r:
            latest_readings[s.sensor_type] = {
                "value": r.value,
                "unit": r.unit,
                "timestamp": r.timestamp.isoformat()
            }

    resp = DeviceResponse.model_validate(device)
    resp.latest_readings = latest_readings
    return resp

@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(device_id: str, device_in: DeviceUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Device).options(selectinload(Device.sensors)).where(Device.id == device_id)
    )
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    if device_in.name is not None:
        device.name = device_in.name
    if device_in.farm_name is not None:
        device.farm_name = device_in.farm_name
    if device_in.location is not None:
        device.location = device_in.location
    if device_in.crop_type is not None:
        device.crop_type = device_in.crop_type
    if device_in.status is not None:
        device.status = device_in.status
    if device_in.ip_address is not None:
        device.ip_address = device_in.ip_address
    if device_in.firmware_version is not None:
        device.firmware_version = device_in.firmware_version
    if device_in.metadata_json is not None:
        device.metadata_json = device_in.metadata_json

    await db.commit()
    await db.refresh(device)
    return DeviceResponse.model_validate(device)

@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    await db.delete(device)
    await db.commit()
    return None
