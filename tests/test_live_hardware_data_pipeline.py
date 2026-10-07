import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.main import app
from app.auth.jwt import create_access_token
from app.database.session import AsyncSessionLocal
from app.models.device import Device
from app.models.reading import SensorReading
from app.services.context_service import context_service
from app.services.ai_service import ai_service
from app.services.rag_service import rag_service

client = TestClient(app)

@pytest.mark.asyncio
async def test_live_hardware_replacement_pipeline():
    """
    Verifies that:
    1. Incoming hardware readings immediately replace/update the current sensor value in the backend.
    2. Every subsequent AI response uses the latest incoming reading without caching stale values.
    3. If physical hardware disconnects, the system clearly indicates 'Last updated X minutes ago'
       and does NOT pretend stale values are current.
    """
    token = create_access_token({"sub": "hardware_engineer", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}
    device_id = "AGRI-DEV-PHYSICAL-TEST"

    # Step 1: Physical hardware transmits Reading 1: 36.4% soil moisture (sub-optimal deficit)
    time_r1 = datetime.now(timezone.utc)
    r1_payload = {
        "device_id": device_id,
        "sensor_id": f"{device_id}-SOIL",
        "sensor_type": "soil_moisture",
        "value": 36.4,
        "unit": "%",
        "timestamp": time_r1.isoformat(),
        "location": "Tomato Plot Sector 1"
    }
    resp1 = client.post("/api/sensors/data", json=r1_payload, headers=headers)
    assert resp1.status_code == 201

    # Verify authoritative status endpoint reflects 36.4% and status LOW
    status_resp1 = client.get(f"/api/sensors/status?device_id={device_id}&crop=Tomato", headers=headers)
    assert status_resp1.status_code == 200
    st1 = status_resp1.json()
    assert st1["evaluations"]["soil_moisture"]["current"] == 36.4
    assert st1["evaluations"]["soil_moisture"]["status"] == "LOW"
    assert st1["status"] == "online"
    assert st1["connection_status"] == "Connected"
    assert st1["is_stale"] is False

    # AI query must use Reading 1 (36.4%)
    chat_resp1 = client.post(
        "/api/voice/chat",
        data={
            "text": "What is the condition of my soil moisture?",
            "crop": "Tomato",
            "device_id": device_id,
            "language_override": "en"
        },
        headers=headers
    )
    assert chat_resp1.status_code == 200
    ans1 = chat_resp1.json()["answer"]
    assert "36.4%" in ans1
    assert "below" in ans1.lower() or "deficit" in ans1.lower()
    assert "within the optimal range" not in ans1.lower()

    # Step 2: Physical hardware transmits Reading 2: 52.8% soil moisture (optimal field capacity after drip irrigation)
    time_r2 = datetime.now(timezone.utc)
    r2_payload = {
        "device_id": device_id,
        "sensor_id": f"{device_id}-SOIL",
        "sensor_type": "soil_moisture",
        "value": 52.8,
        "unit": "%",
        "timestamp": time_r2.isoformat(),
        "location": "Tomato Plot Sector 1"
    }
    resp2 = client.post("/api/sensors/data", json=r2_payload, headers=headers)
    assert resp2.status_code == 201

    # Verify authoritative status endpoint IMMEDIATELY replaced value with 52.8% and status OPTIMAL
    status_resp2 = client.get(f"/api/sensors/status?device_id={device_id}&crop=Tomato", headers=headers)
    assert status_resp2.status_code == 200
    st2 = status_resp2.json()
    assert st2["evaluations"]["soil_moisture"]["current"] == 52.8
    assert st2["evaluations"]["soil_moisture"]["status"] == "OPTIMAL"
    assert st2["evaluations"]["soil_moisture"]["sensor_id"] == f"{device_id}-SOIL"

    # AI query must IMMEDIATELY use Reading 2 (52.8%) without stale caching
    chat_resp2 = client.post(
        "/api/voice/chat",
        data={
            "text": "What is the condition of my soil moisture?",
            "crop": "Tomato",
            "device_id": device_id,
            "language_override": "en"
        },
        headers=headers
    )
    assert chat_resp2.status_code == 200
    ans2 = chat_resp2.json()["answer"]
    assert "52.8%" in ans2
    assert "optimal" in ans2.lower()
    assert "36.4%" not in ans2  # Must not use the old cached reading

    # Step 3: Hardware Disconnection Simulation (Simulate device offline for 15 minutes)
    disconnection_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Device)
            .where(Device.id == device_id)
            .values(last_seen=disconnection_time, status="disconnected")
        )
        await db.execute(
            update(SensorReading)
            .where(SensorReading.device_id == device_id)
            .values(timestamp=disconnection_time)
        )
        await db.commit()

    # Query status endpoint while disconnected
    status_resp3 = client.get(f"/api/sensors/status?device_id={device_id}&crop=Tomato", headers=headers)
    assert status_resp3.status_code == 200
    st3 = status_resp3.json()
    assert st3["status"] == "disconnected"
    assert st3["connection_status"] == "Disconnected"
    assert st3["is_stale"] is True
    assert "Last updated 15 minutes ago" in st3["last_updated_human"]

    # AI query while disconnected must warn user about stale telemetry and NOT pretend reading is current
    chat_resp3 = client.post(
        "/api/voice/chat",
        data={
            "text": "Is my soil moisture sufficient for my tomato crop?",
            "crop": "Tomato",
            "device_id": device_id,
            "language_override": "en"
        },
        headers=headers
    )
    assert chat_resp3.status_code == 200
    ans3 = chat_resp3.json()["answer"]
    # Must flag disconnection or stale notice
    assert "disconnected" in ans3.lower() or "last updated" in ans3.lower() or "stale" in ans3.lower()
