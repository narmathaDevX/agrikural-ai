import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from app.auth.jwt import create_access_token

client = TestClient(app)

def test_api():
    token = create_access_token({"sub": "farmer_test", "role": "farmer"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Post live sensor telemetry matching user's exact values via batch endpoint
    batch_payload = {
        "device_id": "AGRI-TEST-LIVE-001",
        "readings": [
            {"device_id": "AGRI-TEST-LIVE-001", "sensor_id": "TEST-SOIL-1", "sensor_type": "soil_moisture", "value": 36.4, "unit": "%"},
            {"device_id": "AGRI-TEST-LIVE-001", "sensor_id": "TEST-TEMP-1", "sensor_type": "temperature", "value": 26.3, "unit": "°C"},
            {"device_id": "AGRI-TEST-LIVE-001", "sensor_id": "TEST-HUM-1", "sensor_type": "humidity", "value": 74.1, "unit": "%"},
            {"device_id": "AGRI-TEST-LIVE-001", "sensor_id": "TEST-LUX-1", "sensor_type": "light_lux", "value": 614.6, "unit": "lux"},
            {"device_id": "AGRI-TEST-LIVE-001", "sensor_id": "TEST-WAT-1", "sensor_type": "water_level_pct", "value": 10.0, "unit": "%"}
        ]
    }
    resp_ingest = client.post("/api/sensors/batch", json=batch_payload, headers=headers)
    print("INGEST STATUS:", resp_ingest.status_code)

    # 2. Query authoritative sensor agronomic status endpoint
    resp_status = client.get("/api/sensors/status?device_id=AGRI-TEST-LIVE-001&crop=Tomato", headers=headers)
    print("\nAUTHORITATIVE SENSOR STATUS:")
    print(json.dumps(resp_status.json(), indent=2))

    # 3. Ask AI Voice Chat query
    chat_payload = {
        "text": "Is my soil moisture sufficient for my tomato crop?",
        "crop": "Tomato",
        "device_id": "AGRI-TEST-LIVE-001",
        "language_override": "en"
    }
    resp_chat = client.post("/api/voice/chat", data=chat_payload, headers=headers)
    print("\nAI CHAT RESPONSE (Status code:", resp_chat.status_code, "):")
    data = resp_chat.json()
    print("Answer:\n", data.get("answer"))
    print("\nSources:\n", json.dumps(data.get("sources"), indent=2))

if __name__ == "__main__":
    test_api()
