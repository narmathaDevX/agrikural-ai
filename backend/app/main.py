import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.database.session import engine, AsyncSessionLocal
from app.database.base import Base
from app.websocket.manager import ws_manager

# Import all models to ensure metadata registration
import app.models  # noqa
from app.models.user import User
from app.models.device import Device
from app.models.sensor import Sensor
from app.auth.security import get_password_hash
from app.services.rag_service import rag_service
from app.knowledge.ingest import run_ingest
from sqlalchemy import select

# Import routers
from app.api.auth import router as auth_router
from app.api.devices import router as devices_router
from app.api.sensors import router as sensors_router
from app.api.analytics import router as analytics_router
from app.api.alerts import router as alerts_router
from app.api.conversations import router as conversations_router
from app.api.voice import router as voice_router
from app.api.knowledge import router as knowledge_router

logger = logging.getLogger("agrikural.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database Schema
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")

    # 2. Seed Default Admin and Initial Hardware Devices
    async with AsyncSessionLocal() as db:
        # Check admin user
        admin_res = await db.execute(select(User).where(User.email == "admin@agrikural.ai"))
        if not admin_res.scalar_one_or_none():
            admin = User(
                email="admin@agrikural.ai",
                hashed_password=get_password_hash("admin123"),
                full_name="Dr. S. Ramanathan (Agronomist)",
                role="admin",
                preferred_language="ta",
                is_active=True
            )
            db.add(admin)

        # Check default device AGRI-DEV-001
        dev_res = await db.execute(select(Device).where(Device.id == "AGRI-DEV-001"))
        if not dev_res.scalar_one_or_none():
            dev1 = Device(
                id="AGRI-DEV-001",
                name="Greenhouse Sector A - Tomato",
                farm_name="Kural Agro Station, Coimbatore",
                location="Coimbatore, Tamil Nadu",
                crop_type="Tomato",
                status="online",
                ip_address="192.168.1.101",
                firmware_version="v2.4.1",
                metadata_json={"gateway": "ESP32-S3-LTE", "microcontroller": "ESP32", "protocol": "HTTP/REST"}
            )
            db.add(dev1)
            await db.flush()

            # Add default sensors
            sensors = [
                Sensor(id="AGRI-DEV-001-SOIL", device_id="AGRI-DEV-001", sensor_type="soil_moisture", name="Soil Moisture", unit="%", min_threshold=35.0, max_threshold=75.0, critical_min=25.0, critical_max=85.0),
                Sensor(id="AGRI-DEV-001-TEMP", device_id="AGRI-DEV-001", sensor_type="temperature", name="Ambient Temperature", unit="°C", min_threshold=18.0, max_threshold=34.0, critical_min=12.0, critical_max=38.0),
                Sensor(id="AGRI-DEV-001-HUMID", device_id="AGRI-DEV-001", sensor_type="humidity", name="Relative Humidity", unit="%", min_threshold=45.0, max_threshold=80.0, critical_min=30.0, critical_max=90.0),
                Sensor(id="AGRI-DEV-001-LIGHT", device_id="AGRI-DEV-001", sensor_type="light_lux", name="Solar Radiation", unit="lux", min_threshold=200.0, max_threshold=1200.0),
                Sensor(id="AGRI-DEV-001-WATER", device_id="AGRI-DEV-001", sensor_type="water_level_pct", name="Irrigation Tank Level", unit="%", min_threshold=30.0, max_threshold=100.0, critical_min=15.0),
            ]
            db.add_all(sensors)

        # Check secondary device AGRI-DEV-002
        dev2_res = await db.execute(select(Device).where(Device.id == "AGRI-DEV-002"))
        if not dev2_res.scalar_one_or_none():
            dev2 = Device(
                id="AGRI-DEV-002",
                name="Open Field Sector B - Rice Paddy",
                farm_name="Palakkad Agro Fields",
                location="Palakkad, Kerala",
                crop_type="Rice",
                status="online",
                ip_address="192.168.1.102",
                firmware_version="v2.4.1",
                metadata_json={"gateway": "ESP32-S3-LTE", "microcontroller": "ESP32", "protocol": "HTTP/REST"}
            )
            db.add(dev2)
            await db.flush()

            dev2_sensors = [
                Sensor(id="AGRI-DEV-002-SOIL", device_id="AGRI-DEV-002", sensor_type="soil_moisture", name="Paddy Field Water Saturation", unit="%", min_threshold=55.0, max_threshold=90.0),
                Sensor(id="AGRI-DEV-002-TEMP", device_id="AGRI-DEV-002", sensor_type="temperature", name="Canopy Temperature", unit="°C", min_threshold=20.0, max_threshold=36.0),
                Sensor(id="AGRI-DEV-002-HUMID", device_id="AGRI-DEV-002", sensor_type="humidity", name="Relative Humidity", unit="%", min_threshold=50.0, max_threshold=90.0),
            ]
            db.add_all(dev2_sensors)

        await db.commit()
    logger.info("Default seed data verified.")

    # 3. Seed Agricultural Knowledge in ChromaDB if not already indexed
    try:
        if rag_service.collection.count() == 0:
            logger.info("ChromaDB collection empty. Ingesting verified agricultural documents from knowledge_docs/...")
            run_ingest("knowledge_docs")
        else:
            logger.info(f"ChromaDB has {rag_service.collection.count()} chunks indexed.")
    except Exception as e:
        logger.warning(f"Initial document ingestion notice: {e}")

    yield

    logger.info("Shutting down Agrikural system...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered Multilingual Agricultural IoT & RAG Assistant",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(devices_router, prefix=settings.API_V1_STR)
app.include_router(sensors_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)
app.include_router(conversations_router, prefix=settings.API_V1_STR)
app.include_router(voice_router, prefix=settings.API_V1_STR)
app.include_router(knowledge_router, prefix=settings.API_V1_STR)

# Audio static directory
os.makedirs(settings.AUDIO_DIR, exist_ok=True)
app.mount("/api/voice/static", StaticFiles(directory=settings.AUDIO_DIR), name="audio_static")

# WebSocket Live Telemetry endpoint
@app.websocket("/ws")
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "message": "Connected to Agrikural Real-Time IoT & Alert Stream"
        })
        while True:
            # Keep socket alive and receive client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        ws_manager.disconnect(websocket)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "chroma_chunks": rag_service.collection.count()
    }
