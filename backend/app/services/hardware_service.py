import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.device import Device
from app.models.sensor import Sensor
from app.models.reading import SensorReading
from app.models.system_event import SystemEvent
from app.schemas.sensor import SensorReadingCreate
from app.websocket.manager import ws_manager
from app.services.alert_service import alert_service

logger = logging.getLogger("agrikural.hardware")

class HardwareService:
    async def process_sensor_reading(
        self,
        reading_data: SensorReadingCreate,
        db: AsyncSession
    ) -> SensorReading:
        """
        Ingests real-time hardware sensor reading:
        1. Verifies/Registers device and sensor
        2. Logs reading in database
        3. Updates device heartbeat
        4. Triggers threshold alert evaluation
        5. Broadcasts live telemetry over WebSockets to React dashboard
        """
        device_id = reading_data.device_id
        timestamp = reading_data.timestamp or datetime.now(timezone.utc)

        # 1. Update device status and heartbeat
        dev_res = await db.execute(select(Device).where(Device.id == device_id))
        device = dev_res.scalar_one_or_none()

        if not device:
            # Auto-register new hardware device gateway
            device = Device(
                id=device_id,
                name=f"Field Device {device_id}",
                farm_name="Kural Agro Station",
                location=reading_data.location or "Tamil Nadu, India",
                crop_type="Tomato",
                status="online",
                last_seen=timestamp
            )
            db.add(device)
            await db.flush()
        else:
            device.status = "online"
            device.last_seen = timestamp

        # 2. Check/create sensor record
        sensor_res = await db.execute(select(Sensor).where(Sensor.id == reading_data.sensor_id))
        sensor = sensor_res.scalar_one_or_none()
        if not sensor:
            sensor = Sensor(
                id=reading_data.sensor_id,
                device_id=device_id,
                sensor_type=reading_data.sensor_type,
                name=reading_data.sensor_type.replace('_', ' ').title(),
                unit=reading_data.unit,
                is_active=True
            )
            db.add(sensor)
            await db.flush()

        # 3. Store reading
        reading = SensorReading(
            device_id=device_id,
            sensor_id=reading_data.sensor_id,
            sensor_type=reading_data.sensor_type,
            value=reading_data.value,
            unit=reading_data.unit,
            timestamp=timestamp,
            location=reading_data.location,
            metadata_json=reading_data.metadata or {}
        )
        db.add(reading)
        await db.commit()
        await db.refresh(reading)

        # 4. Evaluate alerts
        await alert_service.evaluate_reading(
            device_id=device_id,
            sensor_type=reading_data.sensor_type,
            sensor_id=reading_data.sensor_id,
            value=reading_data.value,
            unit=reading_data.unit,
            db=db
        )

        # 5. Broadcast live reading to connected WebSocket clients
        ws_payload = {
            "type": "SENSOR_READING",
            "data": {
                "id": reading.id,
                "device_id": device_id,
                "sensor_id": reading.sensor_id,
                "sensor_type": reading.sensor_type,
                "value": reading.value,
                "unit": reading.unit,
                "timestamp": reading.timestamp.isoformat(),
                "location": reading.location
            }
        }
        await ws_manager.broadcast_json(ws_payload)

        return reading

    async def process_batch_readings(
        self,
        device_id: str,
        readings: List[SensorReadingCreate],
        db: AsyncSession
    ) -> List[SensorReading]:
        results = []
        for r in readings:
            r.device_id = device_id
            created = await self.process_sensor_reading(r, db)
            results.append(created)
        return results

hardware_service = HardwareService()
