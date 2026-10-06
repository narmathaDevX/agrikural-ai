import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.alert import Alert
from app.models.sensor import Sensor
from app.websocket.manager import ws_manager

logger = logging.getLogger("agrikural.alerts")

class AlertService:
    async def evaluate_reading(
        self,
        device_id: str,
        sensor_type: str,
        sensor_id: str,
        value: float,
        unit: str,
        db: AsyncSession
    ) -> Optional[Alert]:
        """
        Evaluates a sensor reading against sensor thresholds.
        If threshold is violated, creates an alert in DB and broadcasts it via WebSocket.
        """
        # Fetch sensor threshold definition if exists
        query = select(Sensor).where(
            and_(Sensor.device_id == device_id, Sensor.sensor_type == sensor_type)
        )
        res = await db.execute(query)
        sensor = res.scalar_one_or_none()

        min_thresh = sensor.min_threshold if sensor else None
        max_thresh = sensor.max_threshold if sensor else None
        crit_min = sensor.critical_min if sensor else None
        crit_max = sensor.critical_max if sensor else None

        # Default fallback thresholds if not defined on sensor model
        default_thresholds = {
            "soil_moisture": {"min": 35.0, "crit_min": 25.0, "max": 80.0, "crit_max": 90.0},
            "temperature": {"min": 15.0, "crit_min": 10.0, "max": 35.0, "crit_max": 40.0},
            "humidity": {"min": 30.0, "crit_min": 20.0, "max": 85.0, "crit_max": 95.0},
            "water_level_pct": {"min": 30.0, "crit_min": 15.0},
        }

        defaults = default_thresholds.get(sensor_type, {})
        min_thresh = min_thresh if min_thresh is not None else defaults.get("min")
        max_thresh = max_thresh if max_thresh is not None else defaults.get("max")
        crit_min = crit_min if crit_min is not None else defaults.get("crit_min")
        crit_max = crit_max if crit_max is not None else defaults.get("crit_max")

        severity = None
        title = None
        message = None
        violated_thresh = None

        # Check critical thresholds first
        if crit_min is not None and value < crit_min:
            severity = "critical"
            violated_thresh = crit_min
            title = f"Critical Low {sensor_type.replace('_', ' ').title()}"
            message = f"{sensor_type.replace('_', ' ').title()} dropped to {value} {unit} (Critical limit: {crit_min} {unit}). Immediate intervention required!"
        elif crit_max is not None and value > crit_max:
            severity = "critical"
            violated_thresh = crit_max
            title = f"Critical High {sensor_type.replace('_', ' ').title()}"
            message = f"{sensor_type.replace('_', ' ').title()} surged to {value} {unit} (Critical limit: {crit_max} {unit}). Risk of severe crop stress!"
        elif min_thresh is not None and value < min_thresh:
            severity = "warning"
            violated_thresh = min_thresh
            title = f"Low {sensor_type.replace('_', ' ').title()}"
            message = f"{sensor_type.replace('_', ' ').title()} is currently {value} {unit}, below the recommended threshold of {min_thresh} {unit}."
        elif max_thresh is not None and value > max_thresh:
            severity = "warning"
            violated_thresh = max_thresh
            title = f"High {sensor_type.replace('_', ' ').title()}"
            message = f"{sensor_type.replace('_', ' ').title()} is currently {value} {unit}, above the recommended threshold of {max_thresh} {unit}."

        if severity:
            # Check if an unresolved identical alert already exists to prevent alert spamming
            existing_alert_q = select(Alert).where(
                and_(
                    Alert.device_id == device_id,
                    Alert.sensor_type == sensor_type,
                    Alert.is_resolved == False
                )
            )
            existing_res = await db.execute(existing_alert_q)
            existing = existing_res.scalar_one_or_none()

            if not existing:
                new_alert = Alert(
                    device_id=device_id,
                    sensor_id=sensor_id,
                    sensor_type=sensor_type,
                    severity=severity,
                    title=title,
                    message=message,
                    value=value,
                    threshold=violated_thresh,
                    is_resolved=False
                )
                db.add(new_alert)
                await db.commit()
                await db.refresh(new_alert)

                logger.warning(f"ALERT CREATED: [{severity.upper()}] {title} on {device_id}: {message}")

                # Broadcast via WebSocket
                alert_payload = {
                    "type": "NEW_ALERT",
                    "data": {
                        "id": new_alert.id,
                        "device_id": device_id,
                        "sensor_type": sensor_type,
                        "severity": severity,
                        "title": title,
                        "message": message,
                        "value": value,
                        "unit": unit,
                        "threshold": violated_thresh,
                        "created_at": new_alert.created_at.isoformat()
                    }
                }
                await ws_manager.broadcast_json(alert_payload)
                return new_alert

        return None

alert_service = AlertService()
