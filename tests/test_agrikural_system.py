import pytest
import asyncio
from datetime import datetime, timezone

from app.utils.lang_detect import detect_language
from app.services.translation_service import translation_service
from app.services.speech_service import speech_service
from app.services.tts_service import tts_service
from app.knowledge.chunking.chunker import DocumentChunker
from app.services.rag_service import rag_service
from app.services.context_service import context_service
from app.services.ai_service import ai_service
from app.hardware.simulator import AgriHardwareSimulator
from app.auth.security import get_password_hash, verify_password
from app.auth.jwt import create_access_token

@pytest.mark.asyncio
async def test_language_detection():
    # Tamil test
    ta_text = "என் தக்காளி செடிகளுக்கு இந்த மண் ஈரப்பதம் போதுமா?"
    lang_ta, conf_ta = detect_language(ta_text)
    assert lang_ta == "ta"
    assert conf_ta > 0.7

    # Malayalam test
    ml_text = "എന്റെ തക്കാളി ചെടികൾക്ക് ഈ മണ്ണിലെ ഈർപ്പം മതിയോ?"
    lang_ml, conf_ml = detect_language(ml_text)
    assert lang_ml == "ml"
    assert conf_ml > 0.7

    # English test
    en_text = "Is the soil moisture sufficient for my tomato crop?"
    lang_en, conf_en = detect_language(en_text)
    assert lang_en == "en"

@pytest.mark.asyncio
async def test_translation_service():
    # Tamil to English
    ta_q = "மண் ஈரப்பதம் போதுமா? தக்காளி பயிருக்கு எவ்வளவு தண்ணீர் தேவை?"
    res_ta = await translation_service.translate_to_english(ta_q, source_language="ta")
    assert "moisture" in res_ta["translated_text"].lower() or "tomato" in res_ta["translated_text"].lower()
    assert res_ta["source_language"] == "ta"
    assert res_ta["target_language"] == "en"

    # Malayalam to English
    ml_q = "തക്കാളി ചെടികൾക്ക് ഈർപ്പം മതിയോ?"
    res_ml = await translation_service.translate_to_english(ml_q, source_language="ml")
    assert "tomato" in res_ml["translated_text"].lower() or "moisture" in res_ml["translated_text"].lower()

    # English to Tamil
    en_ans = "The current soil moisture is 28%. According to TNAU guidelines, immediate irrigation is recommended."
    res_to_ta = await translation_service.translate_from_english(en_ans, target_language="ta")
    assert len(res_to_ta["translated_text"]) > 0

@pytest.mark.asyncio
async def test_speech_stt_and_tts():
    # STT transcription test with sample audio bytes
    sample_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00"
    stt_res = await speech_service.transcribe_audio(sample_bytes, language_override="ta")
    assert "text" in stt_res
    assert stt_res["language"] == "ta"
    assert stt_res["confidence"] > 0.5

    # TTS generation test for Tamil
    tts_res = await tts_service.generate_speech("மண் ஈரப்பதம் போதுமானது", language="ta")
    assert tts_res["audio_url"] is not None
    assert tts_res["language"] == "ta"

def test_document_chunking():
    chunker = DocumentChunker(target_chunk_size=300, overlap=40)
    sample_doc = """## SECTION 1: SOIL WATER DYNAMICS
Tomato requires adequate soil moisture between 60% and 70%.
Water deficit during flowering stage leads to flower abortion and blossom end rot.

## SECTION 2: NUTRIENT SCHEDULE
Apply N:P:K at 150:100:100 kg per hectare in split doses."""

    chunks = chunker.chunk_text(sample_doc, document_id="doc_test_1", default_metadata={"crop": "Tomato"})
    assert len(chunks) >= 2
    assert chunks[0]["metadata"]["document_id"] == "doc_test_1"
    assert "SECTION" in chunks[0]["metadata"]["section"]

def test_chromadb_rag_retrieval():
    results = rag_service.retrieve("soil moisture requirement for tomato", crop="Tomato", top_k=3)
    assert len(results) > 0
    assert "Tomato" in results[0]["metadata"].get("crop", "")
    sources = rag_service.get_sources(results)
    assert len(sources) > 0
    assert sources[0].document_id is not None

@pytest.mark.asyncio
async def test_ai_grounded_reasoning_and_hallucination_control():
    # Test grounded response with simulated low moisture
    fake_sensor_data = {
        "device_id": "AGRI-DEV-001",
        "crop_type": "Tomato",
        "readings": {
            "soil_moisture": {"value": 24.0, "unit": "%"},
            "temperature": {"value": 31.0, "unit": "°C"}
        }
    }
    retrieved = rag_service.retrieve("soil moisture tomato", crop="Tomato", top_k=2)
    sources = rag_service.get_sources(retrieved)

    reasoning = await ai_service.reason(
        question="Is my soil moisture sufficient for my tomato crop?",
        rag_context="Tomato requires 60% to 70% available soil moisture.",
        sensor_data=fake_sensor_data,
        sources=sources,
        farm_info="Farm: Kural Station | Crop: Tomato",
        crop="Tomato"
    )
    answer = reasoning["answer"]
    assert "24.0%" in answer or "24%" in answer
    assert "below" in answer.lower() or "irrigation" in answer.lower()
    assert len(reasoning["sources"]) > 0

    # Test hallucination control on out-of-domain knowledge without docs
    unsupported_reasoning = await ai_service.reason(
        question="What is the nuclear reactor core temperature?",
        rag_context="",
        sensor_data={"readings": {}},
        sources=[],
        farm_info="",
        crop="Tomato"
    )
    assert "couldn't find enough verified information" in unsupported_reasoning["answer"].lower()

def test_hardware_simulator_telemetry():
    sim = AgriHardwareSimulator(device_id="AGRI-DEV-TEST", interval=1.0)
    readings = sim.generate_telemetry_batch()
    assert len(readings) == 5
    types = [r["sensor_type"] for r in readings]
    assert "soil_moisture" in types
    assert "temperature" in types
    assert "humidity" in types
    assert "light_lux" in types
    assert "water_level_pct" in types

def test_auth_security():
    pwd = "secretFarmerPass2026"
    h = get_password_hash(pwd)
    assert verify_password(pwd, h) is True
    assert verify_password("wrongPass", h) is False

    token = create_access_token({"sub": "user-123", "role": "admin"})
    assert isinstance(token, str)
    assert len(token) > 20
