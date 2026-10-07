import logging
from datetime import datetime, timezone
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
            "status": "disconnected",
            "connection_status": "Disconnected",
            "last_updated_human": "No data received",
            "is_stale": True,
            "last_updated": None
        }

        if not db:
            return sensor_data

        # Auto-resolve device_id if not provided to the most recently active hardware gateway
        if not device_id:
            try:
                latest_dev_res = await db.execute(
                    select(Device).order_by(desc(Device.last_seen)).limit(1)
                )
                latest_dev = latest_dev_res.scalar_one_or_none()
                if latest_dev:
                    device_id = latest_dev.id
            except Exception:
                pass

        if not device_id:
            return sensor_data

        sensor_data["device_id"] = device_id
        now = datetime.now(timezone.utc)

        try:
            # Query device info
            dev_res = await db.execute(select(Device).where(Device.id == device_id))
            device = dev_res.scalar_one_or_none()
            if device:
                sensor_data["device_name"] = device.name
                sensor_data["farm_name"] = device.farm_name
                sensor_data["location"] = device.location
                sensor_data["crop_type"] = device.crop_type
                sensor_data["last_seen"] = device.last_seen.isoformat() if device.last_seen else None

                if device.last_seen:
                    last_seen_dt = device.last_seen if device.last_seen.tzinfo else device.last_seen.replace(tzinfo=timezone.utc)
                    age_seconds = (now - last_seen_dt).total_seconds()
                    sensor_data["age_seconds"] = round(age_seconds, 1)

                    if age_seconds < 60:
                        sensor_data["status"] = "online"
                        sensor_data["connection_status"] = "Connected"
                        sensor_data["last_updated_human"] = "Just now"
                        sensor_data["is_stale"] = False
                    elif age_seconds < 3600:
                        mins = max(1, int(age_seconds // 60))
                        sensor_data["status"] = "disconnected"
                        sensor_data["connection_status"] = "Disconnected"
                        sensor_data["last_updated_human"] = f"Last updated {mins} minute{'s' if mins != 1 else ''} ago"
                        sensor_data["is_stale"] = True
                    elif age_seconds < 86400:
                        hours = int(age_seconds // 3600)
                        sensor_data["status"] = "disconnected"
                        sensor_data["connection_status"] = "Disconnected"
                        sensor_data["last_updated_human"] = f"Last updated {hours} hour{'s' if hours != 1 else ''} ago"
                        sensor_data["is_stale"] = True
                    else:
                        days = int(age_seconds // 86400)
                        sensor_data["status"] = "disconnected"
                        sensor_data["connection_status"] = "Disconnected"
                        sensor_data["last_updated_human"] = f"Last updated {days} day{'s' if days != 1 else ''} ago"
                        sensor_data["is_stale"] = True
                else:
                    sensor_data["status"] = "disconnected"
                    sensor_data["connection_status"] = "Disconnected"
                    sensor_data["last_updated_human"] = "No recent telemetry"
                    sensor_data["is_stale"] = True

            # Fetch latest reading for each sensor type
            subq = await db.execute(
                select(SensorReading)
                .where(SensorReading.device_id == device_id)
                .order_by(desc(SensorReading.timestamp))
                .limit(25)
            )
            readings = subq.scalars().all()

            seen_types = set()
            for r in readings:
                if r.sensor_type not in seen_types:
                    seen_types.add(r.sensor_type)
                    r_dt = r.timestamp if r.timestamp.tzinfo else r.timestamp.replace(tzinfo=timezone.utc)
                    r_age = (now - r_dt).total_seconds()

                    if r_age < 60:
                        age_text = "Just now"
                    elif r_age < 3600:
                        mins = max(1, int(r_age // 60))
                        age_text = f"Last updated {mins}m ago"
                    else:
                        age_text = f"Last updated {int(r_age // 3600)}h ago"

                    is_r_stale = r_age > 60 or sensor_data.get("is_stale", False)
                    sensor_data["readings"][r.sensor_type] = {
                        "value": r.value,
                        "unit": r.unit,
                        "sensor_id": r.sensor_id,
                        "timestamp": r.timestamp.isoformat(),
                        "age_seconds": round(r_age, 1),
                        "is_stale": is_r_stale,
                        "last_updated_text": age_text
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
        is_stale = sensor_context.get("is_stale", False)
        last_updated_human = sensor_context.get("last_updated_human", "recently")
        device_id_str = sensor_context.get("device_id") or "Hardware Gateway"

        if readings:
            if is_stale:
                sensor_blocks.append(
                    f"[HARDWARE ALERT: Physical Device {device_id_str} is DISCONNECTED ({last_updated_human}). "
                    f"Readings are historical and must NOT be treated as current live conditions!]"
                )
            for stype, info in readings.items():
                stale_tag = " [DISCONNECTED / STALE]" if info.get("is_stale") else " [LIVE]"
                sensor_blocks.append(
                    f"- {stype.replace('_', ' ').title()} ({info.get('sensor_id', 'sensor')}): {info['value']} {info['unit']} "
                    f"({info.get('last_updated_text', 'recently')}){stale_tag}"
                )
        else:
            sensor_blocks.append(f"No active physical sensor readings available currently. Hardware {device_id_str} is offline.")

        sensor_context_text = "\n".join(sensor_blocks)
        farm_info_text = f"Farm: {sensor_context.get('farm_name', 'Field Station')} | Location: {effective_region} | Crop: {effective_crop}"

        # 5. Deterministic Agricultural Decision Layer
        from app.services.agricultural_decision_service import agricultural_decision_service
        structured_agri_context = agricultural_decision_service.evaluate_context(
            crop=effective_crop,
            readings=readings,
            retrieved_chunks=retrieved_chunks
        )
        sensor_context["structured_agricultural_context"] = structured_agri_context

        return {
            "question": question,
            "crop": effective_crop,
            "region": effective_region,
            "farm_info": farm_info_text,
            "sensor_context": sensor_context,
            "sensor_context_text": sensor_context_text,
            "retrieved_chunks": retrieved_chunks,
            "rag_context_text": rag_context_text,
            "sources": sources,
            "structured_agricultural_context": structured_agri_context
        }

context_service = ContextService()
