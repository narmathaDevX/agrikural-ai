from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database.session import get_db
from app.models.reading import SensorReading
from app.schemas.sensor import (
    SensorReadingCreate,
    SensorReadingResponse,
    BatchSensorReadings,
)
from app.services.hardware_service import hardware_service

router = APIRouter(prefix="/sensors", tags=["Sensors & Hardware Gateway"])

@router.post("/data", response_model=SensorReadingResponse, status_code=status.HTTP_201_CREATED)
async def ingest_sensor_reading(
    reading_in: SensorReadingCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Primary Gateway Endpoint for Physical IoT Hardware & Simulator.
    Payload:
    {
        "device_id": "AGRI-DEV-001",
        "sensor_id": "AGRI-DEV-001-SOIL",
        "sensor_type": "soil_moisture",
        "value": 24.5,
        "unit": "%",
        "timestamp": "2026-10-06T14:30:00Z",
        "location": "Greenhouse A",
        "metadata": {"depth_cm": 15}
    }
    """
    try:
        created = await hardware_service.process_sensor_reading(reading_in, db)
        return SensorReadingResponse.model_validate(created)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Telemetry ingestion failed: {str(e)}"
        )

@router.post("/batch", response_model=List[SensorReadingResponse], status_code=status.HTTP_201_CREATED)
async def ingest_batch_sensor_readings(
    batch: BatchSensorReadings,
    db: AsyncSession = Depends(get_db)
):
    """Batch hardware ingestion endpoint."""
    created_list = await hardware_service.process_batch_readings(
        device_id=batch.device_id,
        readings=batch.readings,
        db=db
    )
    return [SensorReadingResponse.model_validate(r) for r in created_list]

@router.get("/latest", response_model=List[SensorReadingResponse])
async def get_latest_readings(
    device_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db)
):
    query = select(SensorReading).order_by(desc(SensorReading.timestamp)).limit(limit)
    if device_id:
        query = query.where(SensorReading.device_id == device_id)
    result = await db.execute(query)
    return [SensorReadingResponse.model_validate(r) for r in result.scalars().all()]
