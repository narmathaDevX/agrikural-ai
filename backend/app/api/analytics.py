from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, asc

from app.database.session import get_db
from app.models.reading import SensorReading

router = APIRouter(prefix="/analytics", tags=["Analytics & Timeseries"])

@router.get("/timeseries")
async def get_timeseries_data(
    device_id: Optional[str] = Query(None),
    sensor_type: Optional[str] = Query(None),
    range: str = Query("24h"),  # 1h, 6h, 24h, 7d, 30d
    db: AsyncSession = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    delta_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    time_window = delta_map.get(range, timedelta(hours=24))
    since = now - time_window

    query = select(SensorReading).where(SensorReading.timestamp >= since)
    if device_id:
        query = query.where(SensorReading.device_id == device_id)
    if sensor_type:
        query = query.where(SensorReading.sensor_type == sensor_type)

    query = query.order_by(asc(SensorReading.timestamp)).limit(1000)

    result = await db.execute(query)
    readings = result.scalars().all()

    # Format points for charting
    points = []
    for r in readings:
        points.append({
            "timestamp": r.timestamp.isoformat(),
            "time_label": r.timestamp.strftime("%H:%M" if range in ["1h", "6h", "24h"] else "%b %d %H:%M"),
            "value": round(r.value, 2),
            "unit": r.unit,
            "sensor_type": r.sensor_type,
            "sensor_id": r.sensor_id,
            "device_id": r.device_id
        })

    # Compute quick aggregate statistics
    stats: Dict[str, Any] = {}
    if points:
        values = [p["value"] for p in points]
        stats = {
            "current": values[-1],
            "min": min(values),
            "max": max(values),
            "avg": round(sum(values) / len(values), 2),
            "count": len(values),
            "unit": points[0]["unit"]
        }

    return {
        "device_id": device_id,
        "sensor_type": sensor_type,
        "range": range,
        "stats": stats,
        "data": points
    }

@router.get("/summary")
async def get_farm_summary(
    device_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Returns average, minimum, and maximum of recent key sensors."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    types = ["soil_moisture", "temperature", "humidity", "light_lux", "water_level_pct"]
    summary: Dict[str, Any] = {}

    for st in types:
        q = select(SensorReading).where(
            and_(SensorReading.sensor_type == st, SensorReading.timestamp >= since)
        )
        if device_id:
            q = q.where(SensorReading.device_id == device_id)
        res = await db.execute(q)
        readings = res.scalars().all()
        if readings:
            vals = [r.value for r in readings]
            summary[st] = {
                "current": vals[-1],
                "avg": round(sum(vals) / len(vals), 1),
                "min": min(vals),
                "max": max(vals),
                "unit": readings[0].unit,
            }

    return summary
