import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.device import Device
from app.models.reading import SensorReading
from app.services.rag_service import rag_service

logger = logging.getLogger("agrikural.context")

class ContextService:
    """
    Central hybrid context engine.
    Fuses:
    1. Real-time IoT sensor telemetry
    2. Farm and device metadata
    3. Verified agricultural RAG document chunks
    4. User query
    """

    async def get_latest_sensor_data(
        self,
        device_id: Optional[str],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Retrieves the most recent telemetry readings for each sensor type on the device.
        """
        sensor_data: Dict[str, Any] = {
            "device_id": device_id,
            "readings": {},
            "status": "offline",
            "last_updated": None
        }

        if not device_id or not db:
            return sensor_data

        try:
            # Query device info
            dev_res = await db.execute(select(Device).where(Device.id == device_id))
            device = dev_res.scalar_one_or_none()
            if device:
                sensor_data["device_name"] = device.name
                sensor_data["farm_name"] = device.farm_name
                sensor_data["location"] = device.location
                sensor_data["crop_type"] = device.crop_type
                sensor_data["status"] = device.status
                sensor_data["last_seen"] = device.last_seen.isoformat() if device.last_seen else None

            # Fetch latest reading for each sensor
            subq = await db.execute(
                select(SensorReading)
                .where(SensorReading.device_id == device_id)
                .order_by(desc(SensorReading.timestamp))
                .limit(20)
            )
            readings = subq.scalars().all()

            seen_types = set()
            for r in readings:
                if r.sensor_type not in seen_types:
                    seen_types.add(r.sensor_type)
                    sensor_data["readings"][r.sensor_type] = {
                        "value": r.value,
                        "unit": r.unit,
                        "sensor_id": r.sensor_id,
                        "timestamp": r.timestamp.isoformat()
                    }
        except Exception as e:
            logger.error(f"Error fetching sensor context for {device_id}: {e}")

        return sensor_data

    async def build_context(
        self,
        question: str,
        device_id: Optional[str] = None,
        crop: Optional[str] = None,
        region: Optional[str] = None,
        topic: Optional[str] = None,
        top_k: int = 5,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Combines RAG context, real-time sensor data, and farm metadata.
        """
        # 1. Fetch real-time hardware telemetry
        sensor_context = await self.get_latest_sensor_data(device_id, db)
        
        # Determine crop from device if not explicitly provided
        effective_crop = crop or sensor_context.get("crop_type") or "Tomato"
        effective_region = region or sensor_context.get("location") or "South India"

        # 2. Retrieve semantic agricultural documents
        retrieved_chunks = rag_service.retrieve(
            query=f"{question} for {effective_crop}",
            crop=effective_crop,
            region=effective_region,
            topic=topic,
            top_k=top_k
        )

        sources = rag_service.get_sources(retrieved_chunks)

        # 3. Format RAG text
        context_blocks = []
        for idx, chk in enumerate(retrieved_chunks):
            meta = chk.get("metadata", {})
            title = meta.get("title", "Advisory Document")
            org = meta.get("organization", "ICAR / TNAU")
            page = meta.get("page_number", 1)
            score = chk.get("relevance_score", 0.0)
            context_blocks.append(
                f"[Source {idx + 1}: {title} | {org} | Page {page} | Score: {score:.2f}]\n{chk.get('text')}"
            )
        rag_context_text = "\n\n".join(context_blocks)

        # 4. Format Sensor text
        sensor_blocks = []
        readings = sensor_context.get("readings", {})
        if readings:
            for stype, info in readings.items():
                sensor_blocks.append(f"- {stype.replace('_', ' ').title()}: {info['value']} {info['unit']}")
        else:
            sensor_blocks.append("No active physical sensor readings available currently.")
        
        sensor_context_text = "\n".join(sensor_blocks)
        farm_info_text = f"Farm: {sensor_context.get('farm_name', 'Field Station')} | Location: {effective_region} | Crop: {effective_crop}"

        return {
            "question": question,
            "crop": effective_crop,
            "region": effective_region,
            "farm_info": farm_info_text,
            "sensor_context": sensor_context,
            "sensor_context_text": sensor_context_text,
            "retrieved_chunks": retrieved_chunks,
            "rag_context_text": rag_context_text,
            "sources": sources
        }

context_service = ContextService()
