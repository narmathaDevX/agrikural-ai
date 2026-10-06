# AGRIKURAL AI SYSTEM
### Autonomous Multilingual IoT & Agricultural RAG Assistance Platform

Agrikural AI is an end-to-end, production-grade agricultural assistance platform combining real-time IoT hardware telemetry, automated script detection, bidirectional translation (Tamil ↔ English and Malayalam ↔ English), persistent semantic document retrieval (ChromaDB), and grounded AI reasoning with strict hallucination control and source citations.

---

## 1. System Architecture

```
                 ┌────────────────────────────────────────────────────────┐
                 │          AGRICULTURAL HARDWARE / SIMULATOR             │
                 │      (ESP32 / LoRa / Raspberry Pi / Sensor Array)      │
                 └──────────────────────────┬─────────────────────────────┘
                                            │ HTTP POST / WebSocket
                                            ▼
                 ┌────────────────────────────────────────────────────────┐
                 │                FASTAPI BACKEND CORE                    │
                 │              (Hardware Gateway & API)                  │
                 └───────────────┬───────────────────────┬────────────────┘
                                 │                       │
                ┌────────────────┴──────────────┐        │
                ▼                               ▼        │
         PostgreSQL / DB                  WebSockets     │
      (Historical Telemetry,           (Real-Time Live   │
       Audit Logs, Alerts)                 Broadcast)    │
                                                │        │
                                                ▼        │
                                         React Dashboard │
                                                         ▼
                                          ┌─────────────────────────────┐
                                          │      AI REASONING LAYER     │
                                          └──────────────┬──────────────┘
                                                         │
                        ┌────────────────────────────────┴──────────────────────────────┐
                        ▼                                                               ▼
       ┌───────────────────────────────────┐                         ┌───────────────────────────────────┐
       │      MULTILINGUAL VOICE PIPELINE   │                         │     GROUNDED RAG KNOWLEDGE BASE   │
       │                                   │                         │                                   │
       │ • Tamil / Malayalam / English     │                         │ • Verified University Documents   │
       │ • Speech-to-Text (STT)            │                         │   (TNAU, ICAR, KAU)               │
       │ • Unicode Script Language Detect  │                         │ • Section-Aware Chunking          │
       │ • Bidirectional Translation       │                         │ • Multilingual Embeddings         │
       │ • Text-to-Speech (TTS Audio)      │                         │ • ChromaDB Persistent Vectors     │
       └───────────────────────────────────┘                         └───────────────────────────────────┘
```

---

## 2. Core Technological Architecture

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.12+) | High-throughput async REST and WebSockets |
| **Database** | PostgreSQL + SQLAlchemy 2.0 | Async connection pooling with automatic SQLite dev fallback |
| **Vector Database** | ChromaDB (`chromadb`) | Persistent vector storage in `data/chroma_db` |
| **Embeddings** | SentenceTransformers / Dense Semantic Vectorizer | 384-dimensional multilingual vector space |
| **Frontend** | React 19 + TypeScript + Vite | Tailwind CSS v4, Lucide icons, Recharts |
| **Speech-to-Text** | Whisper / Local Acoustic Adapter | Tamil (`ta`), Malayalam (`ml`), English (`en`) |
| **Translation** | IndicTrans / Domain-Specific Bilingual Engine | Tamil ↔ English, Malayalam ↔ English |
| **Text-to-Speech** | gTTS / Local Neural Audio Engine | Native Tamil, Malayalam, and English audio |
| **IoT Gateway** | REST (`/api/sensors/data`) & WebSockets (`/ws`) | Generic sensor schema supporting any microcontroller |

---

## 3. Project Directory Structure

```
agrikural-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint, lifespan & WebSockets
│   │   ├── config/settings.py       # Pydantic Settings & environment variables
│   │   ├── database/
│   │   │   ├── base.py              # DeclarativeBase & timestamp helpers
│   │   │   └── session.py           # AsyncSession engine (Postgres / SQLite)
│   │   ├── models/                  # SQLAlchemy models (User, Device, Sensor, Reading, Alert, Conversation, Document)
│   │   ├── schemas/                 # Pydantic validation schemas
│   │   ├── auth/                    # JWT authentication & bcrypt security
│   │   ├── api/                     # API routers (auth, devices, sensors, analytics, alerts, voice, knowledge)
│   │   ├── services/
│   │   │   ├── ai_service.py        # Grounded reasoning & hallucination control
│   │   │   ├── translation_service.py # Tamil/Malayalam ↔ English translation
│   │   │   ├── speech_service.py    # Speech-to-text service
│   │   │   ├── tts_service.py       # Text-to-speech audio synthesizer
│   │   │   ├── embedding_service.py # Multilingual vector embeddings
│   │   │   ├── rag_service.py       # ChromaDB vector retrieval & ingestion
│   │   │   ├── context_service.py   # Hybrid Context Builder (Telemetry + RAG)
│   │   │   ├── hardware_service.py  # IoT packet ingestion & alert triggers
│   │   │   └── alert_service.py     # Threshold breach evaluator
│   │   ├── knowledge/
│   │   │   ├── ingest.py            # Document ingestion CLI (`python -m app.knowledge.ingest`)
│   │   │   └── chunking/chunker.py  # Intelligent section & paragraph chunker
│   │   ├── hardware/
│   │   │   └── simulator.py         # Autonomous physical telemetry simulator
│   │   ├── websocket/manager.py     # Connection manager & live telemetry broadcaster
│   │   └── utils/
│   │       ├── lang_detect.py       # High precision Tamil/Malayalam/English script detector
│   │       └── logger.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/              # Sidebar, Header, Modals
│   │   ├── context/                 # AuthContext, WebSocketContext
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx        # Live real-time dashboard with WebSockets
│   │   │   ├── Assistant.tsx        # Multilingual voice/text chat with citations & sensor snapshot
│   │   │   ├── VoiceStudio.tsx      # Push-to-talk recording studio & pipeline visualizer
│   │   │   ├── Devices.tsx          # IoT device registration & gateway status
│   │   │   ├── Analytics.tsx        # Timeseries graphs (1h, 6h, 24h, 7d, 30d)
│   │   │   ├── Alerts.tsx           # Configurable threshold alert center
│   │   │   ├── History.tsx          # Consultation audit trail & source references
│   │   │   ├── Knowledge.tsx        # Document upload, search & RAG debug diagnostic
│   │   │   └── Login.tsx            # Auth screen with 1-click demo profiles
│   │   ├── services/api.ts          # Central REST API client
│   │   └── types/index.ts           # TypeScript interfaces
│   ├── Dockerfile
│   └── package.json
├── knowledge_docs/                  # Bundled verified agricultural reference guides
│   ├── TNAU_Tomato_Cultivation_and_Irrigation_Guide.txt
│   ├── ICAR_Rice_Paddy_Water_and_Nutrient_Management.txt
│   ├── TNAU_Chilli_Crop_Production_Guide.txt
│   └── KAU_Coconut_Palm_Irrigation_and_Fertilizer_Advisory.txt
├── tests/
│   └── test_agrikural_system.py     # Comprehensive automated test suite
├── docker-compose.yml
└── README.md
```

---

## 4. Quick Start Guide

### Step 1: Clone and Setup Virtual Environment

```bash
cd agrikural-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

```bash
cp .env.example .env
```

The application defaults to SQLite (`sqlite+aiosqlite:///./data/agrikural.db`) for immediate offline execution without external dependencies. If running PostgreSQL:
```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/agrikural
```

### Step 3: Ingest Verified Agricultural Knowledge Documents

Run the automated ingestion pipeline to extract, chunk, embed, and index documents into ChromaDB:

```bash
PYTHONPATH=backend python -m app.knowledge.ingest
```

### Step 4: Run the Backend Server

Start the FastAPI application on port 8000:

```bash
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Docs (Swagger UI): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### Step 5: Start the Frontend Application

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

**Demo Credentials (or use 1-click buttons on the login page):**
- **Agronomist (Admin):** `admin@agrikural.ai` / `admin123`
- **Farmer Account:** `farmer@agrikural.ai` / `farmer123`

### Step 6: Start the Real Hardware Telemetry Simulator

In a separate terminal, launch the autonomous hardware simulator:

```bash
PYTHONPATH=backend python -m app.hardware.simulator --device AGRI-DEV-001 --interval 3.0
```

*Watch the React Dashboard update live via WebSockets every 3 seconds without refreshing!*

---

## 5. End-to-End Verification Flows

### Flow 1: Hardware Telemetry to Dashboard
1. The hardware simulator transmits sensor readings via `POST /api/sensors/data`.
2. The FastAPI backend logs the reading into PostgreSQL (`sensor_readings`).
3. The threshold engine checks limits (e.g. soil moisture < 25%).
4. The WebSocket manager broadcasts `SENSOR_READING` to connected clients.
5. The React Dashboard updates live gauges and charts with zero browser reload.

### Flow 2: Document Ingestion to Semantic Retrieval
1. Place a PDF, TXT, or DOCX document in `knowledge_docs/` or upload via the Knowledge Management page (`/knowledge`).
2. The system executes section-aware intelligent chunking.
3. Chunks are embedded and stored in persistent ChromaDB (`agriculture_knowledge`).
4. Queries retrieve the top-K chunks with similarity scores and page numbers.

### Flow 3: Multilingual Voice Pipeline
1. The user speaks in Tamil ("என் தக்காளி செடிகளுக்கு இந்த மண் ஈரப்பதம் போதுமா?").
2. The speech service transcribes audio and detects Tamil (`ta`).
3. The translation service translates to English ("Is the current soil moisture level sufficient for tomato crop?").
4. The hybrid context builder fetches live sensor readings for the device (e.g. Soil moisture = 28%).
5. The RAG retriever finds matching TNAU tomato guidelines.
6. The AI synthesizes a grounded answer citing TNAU.
7. The answer is translated back to Tamil.
8. Text-to-Speech generates spoken Tamil audio, automatically playing back to the user.

### Flow 4: Grounded Soil Moisture Evaluation (Sensor + RAG)
- **Current Sensor Value:** `Soil moisture = 24.5%`
- **Crop:** `Tomato`
- **Question:** "Is the soil moisture sufficient?"
- **AI Response:**
  > "Your current soil moisture is at **24.5%**, which is below the optimal threshold (45% - 65%) for Tomato.
  >
  > According to **Tamil Nadu Agricultural University (TNAU)** (*Production Technology and Water Management in Tomato*), prolonged moisture stress during flowering and fruit setting leads to blossom end rot and flower drop. **Immediate drip irrigation is recommended** for 1.5 to 2 hours."

---

## 6. Physical Hardware Connection Guide

The system is designed for direct physical hardware integration. Microcontrollers (such as ESP32, ESP8266, Raspberry Pi Pico W, Arduino with Ethernet/WiFi) should send telemetry to:

### HTTP Endpoint
- **URL:** `POST http://<SERVER_IP>:8000/api/sensors/data`
- **Headers:** `Content-Type: application/json`

### JSON Payload Schema
```json
{
  "device_id": "AGRI-DEV-001",
  "sensor_id": "AGRI-DEV-001-SOIL",
  "sensor_type": "soil_moisture",
  "value": 28.5,
  "unit": "%",
  "timestamp": "2026-10-06T15:00:00Z",
  "location": "Greenhouse Sector A",
  "metadata": {
    "depth_cm": 15,
    "battery_v": 3.7
  }
}
```

### Arduino / ESP32 C++ Code Example
```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "http://192.168.1.100:8000/api/sensors/data";

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    float soilValue = analogRead(34) * (100.0 / 4095.0); // Example capacitive sensor
    String payload = "{\"device_id\":\"AGRI-DEV-001\",\"sensor_id\":\"AGRI-DEV-001-SOIL\",\"sensor_type\":\"soil_moisture\",\"value\":" + String(soilValue, 1) + ",\"unit\":\"%\"}";

    int httpCode = http.POST(payload);
    http.end();
  }
  delay(5000); // Send every 5 seconds
}
```

---

## 7. Model Adapter Configuration

The system uses a modular adapter architecture in `backend/app/config/settings.py` so any model can be swapped via `.env`:

| Component | Default Adapter | Configurable Options |
| :--- | :--- | :--- |
| **STT** | `local` (Whisper / Local Acoustic) | `whisper`, `hf`, `mock` |
| **Translation** | `local` (IndicTrans domain engine) | `indictrans`, `marian`, `hf` |
| **TTS** | `gtts` (Google Text-to-Speech) | `gtts`, `local`, `edge_tts` |
| **Embeddings** | `local` (Dense multilingual vectorizer) | `sentence_transformers`, `onnx` |
| **LLM Reasoning** | `local` (Grounded agronomic engine) | `ollama`, `openai`, `gemini`, `huggingface` |

To connect a local Ollama model (e.g. LLaMA-3 or Mistral):
```ini
LLM_PROVIDER=ollama
LLM_MODEL=llama3:8b
LLM_API_BASE=http://localhost:11434/v1
```

---

## 8. Running Automated Tests

Run the comprehensive test suite verifying authentication, telemetry ingestion, chunking, ChromaDB retrieval, grounded AI reasoning, translation, and speech generation:

```bash
PYTHONPATH=backend pytest tests/test_agrikural_system.py -o asyncio_mode=auto -v
```

All 8 tests pass with zero warnings!

---

## 9. Running with Docker Compose

To run the entire system including PostgreSQL, FastAPI backend, and React frontend inside containers:

```bash
docker-compose up --build -d
```
