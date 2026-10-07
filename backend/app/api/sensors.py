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

@router.get("/status")
async def get_sensor_agronomic_status(
    device_id: str = Query("AGRI-DEV-001"),
    crop: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Authoritative single source of truth for agricultural thresholds & status.
    Compares live sensor values directly with verified RAG reference guidelines.
    """
    from app.services.context_service import context_service
    from app.services.agricultural_decision_service import agricultural_decision_service
    from app.services.rag_service import rag_service

    # Fetch latest sensor readings for device
    sensor_data = await context_service.get_latest_sensor_data(device_id, db)
    effective_crop = crop or sensor_data.get("crop_type") or "Tomato"
    readings = sensor_data.get("readings", {})

    # Retrieve RAG chunks for crop
    retrieved_chunks = rag_service.retrieve(
        query=f"soil moisture temperature guidelines for {effective_crop}",
        crop=effective_crop,
        top_k=5
    )

    evaluation_context = agricultural_decision_service.evaluate_context(
        crop=effective_crop,
        readings=readings,
        retrieved_chunks=retrieved_chunks
    )

    return {
        "device_id": sensor_data.get("device_id") or device_id,
        "crop": effective_crop,
        "status": sensor_data.get("status", "disconnected"),
        "connection_status": sensor_data.get("connection_status", "Disconnected"),
        "last_seen": sensor_data.get("last_seen"),
        "last_updated_human": sensor_data.get("last_updated_human", "No recent telemetry"),
        "is_stale": sensor_data.get("is_stale", True),
        "age_seconds": sensor_data.get("age_seconds"),
        "evaluations": evaluation_context["evaluations"],
        "agricultural_reference": evaluation_context["agricultural_reference"],
        "computed_status": evaluation_context["computed_status"],
        "readings": readings
    }

