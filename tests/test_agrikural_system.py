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
from app.services.agricultural_decision_service import agricultural_decision_service
from app.services.response_validation_service import response_validation_service
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

def test_agricultural_decision_service_deterministic_bounds():
    """
    Validates deterministic decision logic against university RAG thresholds.
    Ensures mathematical correctness:
    - Case 1: 36.4% is strictly < 45.0% -> LOW (NOT OPTIMAL)
    - Case 2: 54.0% is within [45.0%, 65.0%] -> OPTIMAL
    - Case 3: 72.0% is strictly > 65.0% -> HIGH
    """
    # Case 1: 36.4% moisture for Tomato
    eval_case1 = agricultural_decision_service.evaluate_context(
        crop="Tomato",
        sensor_readings={
            "soil_moisture": 36.4,
            "temperature": 26.3,
            "humidity": 74.1,
            "water_level": 10.0,
            "light": 614.6
        }
    )
    status_case1 = eval_case1["computed_status"]
    evals_case1 = eval_case1["evaluations"]
    ref_case1 = eval_case1["agricultural_reference"]

    # Soil moisture: 36.4 < 45.0 -> MUST BE LOW
    assert status_case1["soil_moisture"] == "LOW"
    assert evals_case1["soil_moisture"]["current"] == 36.4
    assert evals_case1["soil_moisture"]["minimum"] == 45.0
    assert evals_case1["soil_moisture"]["maximum"] == 65.0
    assert "TNAU Tomato Cultivation and Irrigation Guide" in evals_case1["soil_moisture"]["source_document"]

    # Water level: 10.0 < 30.0 -> LOW
    assert status_case1["water_level"] == "LOW"
    # Temp 26.3 within [20, 32] -> OPTIMAL
    assert status_case1["temperature"] == "OPTIMAL"
    # Humidity 74.1 within [45, 75] -> OPTIMAL
    assert status_case1["humidity"] == "OPTIMAL"

    # Case 2: 54.0% moisture for Tomato -> OPTIMAL
    eval_case2 = agricultural_decision_service.evaluate_context(
        crop="Tomato",
        sensor_readings={"soil_moisture": 54.0, "temperature": 26.3}
    )
    assert eval_case2["computed_status"]["soil_moisture"] == "OPTIMAL"
    assert eval_case2["evaluations"]["soil_moisture"]["status"] == "OPTIMAL"

    # Case 3: 72.0% moisture for Tomato -> HIGH
    eval_case3 = agricultural_decision_service.evaluate_context(
        crop="Tomato",
        sensor_readings={"soil_moisture": 72.0, "temperature": 26.3}
    )
    assert eval_case3["computed_status"]["soil_moisture"] == "HIGH"
    assert eval_case3["evaluations"]["soil_moisture"]["status"] == "HIGH"

def test_response_validation_service_rejection_and_enforcement():
    """
    Validates that ResponseValidationService intercepts contradictory candidate responses
    (e.g., claiming 36.4% is optimal when status is LOW) and removes ungrounded irrigation durations.
    """
    structured_context = {
        "crop": "Tomato",
        "sensor": {
            "soil_moisture": 36.4,
            "temperature": 26.3,
            "humidity": 74.1,
            "water_level": 10.0
        },
        "agricultural_reference": {
            "soil_moisture": {
                "minimum": 45.0,
                "maximum": 65.0,
                "unit": "%",
                "source": "TNAU Tomato Cultivation and Irrigation Guide",
                "organization": "Tamil Nadu Agricultural University (TNAU)"
            }
        },
        "computed_status": {
            "soil_moisture": "LOW",
            "temperature": "OPTIMAL",
            "humidity": "OPTIMAL",
            "water_level": "LOW"
        }
    }

    # Flawed candidate output mimicking original hallucination bug
    flawed_llm_response = (
        "Your current soil moisture is at 36.4%, which is within the optimal range (45%–65%) for Tomato. "
        "No immediate additional watering is required. Apply drip irrigation for 1.5 to 2 hours."
    )

    final_resp, is_valid, violation_log = response_validation_service.validate_and_enforce(
        candidate_response=flawed_llm_response,
        structured_context=structured_context
    )

    # Must be caught as invalid and corrected
    assert is_valid is False
    assert "Numerical contradiction" in violation_log
    assert "36.4%" in final_resp
    assert "below" in final_resp.lower()
    assert "optimal range" in final_resp.lower()
    # Must NOT contain the contradiction in the final output
    assert "which is within the optimal" not in final_resp
    assert "no immediate additional watering is required" not in final_resp
    assert "for 1.5 to 2 hours" not in final_resp
    # Must cite TNAU
    assert "Tamil Nadu Agricultural University (TNAU)" in final_resp

@pytest.mark.asyncio
async def test_ai_reasoning_pipeline_cases_1_2_3():
    """
    Tests end-to-end AI reasoning with deterministic agricultural context and validation:
    Case 1: 36.4% -> Explains moisture is below 45%-65%, status is LOW, warns about low water reservoir (10%)
    Case 2: 54.0% -> Explains moisture is within optimal range (45%-65%)
    Case 3: 72.0% -> Explains moisture is above optimal range (45%-65%) and withholds watering
    """
    # CASE 1: The user's exact reported bug condition
    case1_sensor_data = {
        "device_id": "AGRI-DEV-001",
        "crop_type": "Tomato",
        "readings": {
            "soil_moisture": {"value": 36.4, "unit": "%"},
            "temperature": {"value": 26.3, "unit": "°C"},
            "humidity": {"value": 74.1, "unit": "%"},
            "light_lux": {"value": 614.6, "unit": "lux"},
            "water_level_pct": {"value": 10.0, "unit": "%"}
        }
    }

    retrieved = rag_service.retrieve("soil moisture tomato irrigation", crop="Tomato", top_k=2)
    sources = rag_service.get_sources(retrieved)
    rag_context = "\n\n".join([f"[{c.get('metadata', {}).get('title', 'Advisory')}]: {c.get('text', '')}" for c in retrieved])

    reasoning_case1 = await ai_service.reason(
        question="Is my soil moisture sufficient for my tomato crop?",
        rag_context=rag_context,
        sensor_data=case1_sensor_data,
        sources=sources,
        farm_info="Farm: Kural Alpha | Crop: Tomato",
        crop="Tomato"
    )

    answer_1 = reasoning_case1["answer"]
    evals_1 = reasoning_case1["evaluations"]

    assert evals_1["soil_moisture"]["status"] == "LOW"
    assert evals_1["soil_moisture"]["current"] == 36.4
    assert evals_1["soil_moisture"]["minimum"] == 45.0
    assert evals_1["soil_moisture"]["maximum"] == 65.0
    # The answer MUST NOT say 36.4% is optimal or within optimal range!
    assert "within the optimal range" not in answer_1.lower()
    assert "is optimal" not in answer_1.lower()
    assert "no immediate additional watering is required" not in answer_1.lower()
    assert "below" in answer_1.lower() or "deficit" in answer_1.lower()
    # No hallucinated duration
    assert "for 1.5 to 2 hours" not in answer_1.lower()
    # Water reservoir warning
    assert "water level" in answer_1.lower() or "reservoir" in answer_1.lower()

    # CASE 2: Optimal soil moisture (54.0%)
    case2_sensor_data = {
        "device_id": "AGRI-DEV-001",
        "crop_type": "Tomato",
        "readings": {
            "soil_moisture": {"value": 54.0, "unit": "%"},
            "temperature": {"value": 26.3, "unit": "°C"},
            "humidity": {"value": 74.1, "unit": "%"}
        }
    }
    reasoning_case2 = await ai_service.reason(
        question="What is the condition of my soil moisture?",
        rag_context=rag_context,
        sensor_data=case2_sensor_data,
        sources=sources,
        farm_info="Farm: Kural Alpha | Crop: Tomato",
        crop="Tomato"
    )
    answer_2 = reasoning_case2["answer"]
    assert reasoning_case2["evaluations"]["soil_moisture"]["status"] == "OPTIMAL"
    assert "optimal" in answer_2.lower()

    # CASE 3: Excessive soil moisture (72.0%)
    case3_sensor_data = {
        "device_id": "AGRI-DEV-001",
        "crop_type": "Tomato",
        "readings": {
            "soil_moisture": {"value": 72.0, "unit": "%"},
            "temperature": {"value": 26.3, "unit": "°C"},
            "humidity": {"value": 74.1, "unit": "%"}
        }
    }
    reasoning_case3 = await ai_service.reason(
        question="Should I irrigate my tomato crop now?",
        rag_context=rag_context,
        sensor_data=case3_sensor_data,
        sources=sources,
        farm_info="Farm: Kural Alpha | Crop: Tomato",
        crop="Tomato"
    )
    answer_3 = reasoning_case3["answer"]
    assert reasoning_case3["evaluations"]["soil_moisture"]["status"] == "HIGH"
    assert "above" in answer_3.lower() or "withhold" in answer_3.lower() or "excessive" in answer_3.lower()

