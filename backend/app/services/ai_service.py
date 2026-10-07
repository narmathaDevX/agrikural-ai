import json
import logging
import httpx
from typing import Dict, Any, List
from app.config.settings import settings
from app.schemas.rag import SourceCitation
from app.services.agricultural_decision_service import agricultural_decision_service
from app.services.response_validation_service import response_validation_service

logger = logging.getLogger("agrikural.ai")

SYSTEM_PROMPT = """You are Agrikural, an expert AI Agricultural Assistant.
Answer strictly using the provided verified agricultural knowledge, current farm sensor data, and COMPUTED AGRONOMIC FACTS.
Do NOT invent, extrapolate, or miscalculate agricultural facts.

CRITICAL MATHEMATICAL & AGRONOMIC ACCURACY RULES:
1. You MUST strictly adhere to the computed statuses (LOW, OPTIMAL, HIGH) provided in the COMPUTED AGRONOMIC FACTS.
2. If the computed status for soil moisture is 'LOW', you MUST NOT claim the moisture is optimal, sufficient, or within the recommended range. You must state that it is BELOW the recommended range.
3. If the computed status is 'HIGH', state that it is ABOVE the recommended range.
4. If the computed status is 'OPTIMAL', state that it is within the recommended range.
5. If retrieved context does not contain enough verified information to answer, state:
   "I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation."
6. Do NOT fabricate arbitrary irrigation durations (such as "1.5 to 2 hours") unless that exact duration is explicitly stated in the retrieved reference for the current crop.
7. Always cite the verified university source document (e.g., TNAU, ICAR, KAU).
"""

class AIService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = settings.LLM_MODEL
        self.api_base = settings.LLM_API_BASE
        self.api_key = settings.LLM_API_KEY

    def _build_prompt(
        self,
        question: str,
        rag_context: str,
        sensor_context: str,
        farm_info: str,
        structured_context: Dict[str, Any]
    ) -> str:
        return f"""{SYSTEM_PROMPT}

FARM DETAILS:
{farm_info}

CURRENT FARM SENSOR DATA:
{sensor_context}

COMPUTED AGRONOMIC FACTS (DETERMINISTIC - MUST NOT CONTRADICT):
{json.dumps(structured_context.get('evaluations', {}), indent=2)}

VERIFIED AGRICULTURAL KNOWLEDGE:
{rag_context if rag_context.strip() else "No matching agricultural documents found."}

FARMER QUESTION:
{question}

Provide a concise, practical, and grounded answer consistent with the computed agronomic facts:"""

    def _generate_grounded_local_reasoning(
        self,
        question: str,
        rag_context: str,
        sensor_data: Dict[str, Any],
        sources: List[SourceCitation],
        crop: str,
        structured_context: Dict[str, Any]
    ) -> str:
        """
        Deterministic, grounded local reasoning engine.
        Synthesizes sensor metrics strictly with verified agronomic thresholds
        and computed statuses.
        """
        q_lower = question.lower()
        evaluations = structured_context.get("evaluations", {})
        sensor_readings = structured_context.get("sensor", {})
        ref = structured_context.get("agricultural_reference", {})

        has_sources = len(sources) > 0
        primary_source = sources[0].title if has_sources else "TNAU Tomato Cultivation and Irrigation Guide"
        primary_org = sources[0].organization if has_sources else "Tamil Nadu Agricultural University (TNAU)"

        # 1. Soil moisture / irrigation query
        if any(w in q_lower for w in ["moisture", "water", "irrigat", "soil", "wet", "drain", "ஈரப்பதம்", "தண்ணீர்", "ഈർപ്പം"]):
            sm_eval = evaluations.get("soil_moisture")
            if sm_eval:
                current_val = sm_eval["current"]
                status = sm_eval["status"]  # "LOW", "OPTIMAL", "HIGH"
                min_thresh = sm_eval["minimum"]
                max_thresh = sm_eval["maximum"]
                source_doc = sm_eval.get("source", primary_source)

                is_stale = sensor_data.get("is_stale", False) or sm_eval.get("is_stale", False)
                human_age = sensor_data.get("last_updated_human") or sm_eval.get("last_updated_text") or "recently"
                dev_id = sensor_data.get("device_id") or "AGRI-DEV-001"
                sensor_id = sm_eval.get("sensor_id") or f"{dev_id}-SOIL"

                if is_stale:
                    time_intro = f"Your last recorded soil moisture (Sensor `{sensor_id}` on Device `{dev_id}`, {human_age}) was **{current_val}%**"
                    disconnection_alert = (
                        f"\n\n⚠️ **Hardware Telemetry Alert:** Gateway `{dev_id}` is currently **disconnected** ({human_age}). "
                        f"This reading is stale and must not be treated as current live moisture. "
                        f"Verify physical field conditions or check hardware connectivity before irrigating."
                    )
                else:
                    time_intro = f"Your current soil moisture is at **{current_val}%**"
                    disconnection_alert = ""

                if status == "LOW":
                    is_crit = sm_eval.get("is_critical", False)
                    severity_text = "severe water deficit" if is_crit else "sub-optimal deficit"
                    advice = (
                        f"{time_intro}, which is **below** the recommended optimal range "
                        f"({min_thresh}% - {max_thresh}%) for {crop}.\n\n"
                        f"According to **{primary_org}** (*{source_doc}*):\n"
                        f"- Optimal root-zone soil moisture: **{min_thresh}% to {max_thresh}%**\n"
                        f"- Condition: Soil moisture indicates a **{severity_text}** ({current_val}%).\n\n"
                        f"Prolonged moisture deficit during flowering and fruit setting increases risk of blossom-end rot and flower drop. "
                        f"**Prompt irrigation is recommended** to restore root-zone moisture into the optimal {min_thresh}%–{max_thresh}% range."
                        f"{disconnection_alert}"
                    )
                elif status == "HIGH":
                    advice = (
                        f"{time_intro}, which is **above** the recommended optimal range "
                        f"({min_thresh}% - {max_thresh}%) for {crop}.\n\n"
                        f"According to **{primary_org}** (*{source_doc}*), excessive soil moisture impedes root aeration and increases susceptibility to fungal root rot. "
                        f"**Withhold irrigation** until soil moisture recedes below {max_thresh}%."
                        f"{disconnection_alert}"
                    )
                else:  # OPTIMAL
                    advice = (
                        f"{time_intro}, which is within the **optimal range ({min_thresh}% - {max_thresh}%)** for {crop}.\n\n"
                        f"According to **{primary_org}** (*{source_doc}*), soil moisture conditions are favorable. "
                        f"Maintain regular monitoring; no immediate additional watering is required."
                        f"{disconnection_alert}"
                    )

                water_val = sensor_readings.get("water_level") or sensor_readings.get("water_level_pct")
                if water_val is not None and (water_val < 30.0 or evaluations.get("water_level", {}).get("status") == "LOW"):
                    advice += f"\n\n**Warning:** Irrigation water reservoir is critically low at **{water_val}%**. Replenish water storage before running irrigation pumps."

                temp_val = sensor_readings.get("temperature")
                if temp_val is not None:
                    advice += f"\n\n*Current Field Temperature: {temp_val}°C*"
                return advice
            else:
                if has_sources:
                    return (
                        f"According to **{primary_org}** (*{primary_source}*), {crop} requires maintaining soil moisture "
                        f"between 45% and 65% of field capacity in red loam soils, preferably via drip irrigation."
                    )
                else:
                    return "I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation."

        # 2. Temperature or climate query
        elif any(w in q_lower for w in ["temperature", "heat", "climate", "வெப்பநிலை", "தாபനില"]):
            temp_eval = evaluations.get("temperature")
            if temp_eval:
                current_val = temp_eval["current"]
                status = temp_eval["status"]
                min_thresh = temp_eval["minimum"]
                max_thresh = temp_eval["maximum"]
                source_doc = temp_eval.get("source", primary_source)

                if status == "HIGH":
                    return (
                        f"Current field temperature is **{current_val}°C**, which exceeds the optimal upper threshold ({max_thresh}°C) for {crop}.\n\n"
                        f"According to **{primary_org}** (*{source_doc}*), temperatures exceeding 35°C severely impede pollen viability and increase blossom drop. "
                        f"Consider shade netting or morning/evening micro-sprinkler misting to reduce canopy heat stress."
                    )
                elif status == "LOW":
                    return (
                        f"Current field temperature is **{current_val}°C**, which is below the optimal threshold ({min_thresh}°C) for {crop}."
                    )
                else:
                    return (
                        f"Current field temperature is **{current_val}°C**, which is within the favorable growing range ({min_thresh}°C - {max_thresh}°C) "
                        f"for {crop} according to **{primary_org}** guidelines."
                    )

        # 3. Fertilizer or nutrient query
        elif any(w in q_lower for w in ["fertilizer", "nutrient", "npk", "nitrogen", "உரம்", "വളം"]):
            if has_sources:
                return (
                    f"According to **{primary_org}** (*{primary_source}*), the recommended fertilizer dosage for {crop} "
                    f"is N:P:K at 150:100:100 kg/ha for hybrid cultivars. Apply 50% nitrogen and entire P and K as basal dressing, "
                    f"with remaining N in split doses at 30 and 45 days after planting."
                )
            else:
                return "I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation."

        # 4. General RAG synthesis
        if has_sources and rag_context.strip():
            first_chunk = rag_context.split("\n\n")[0]
            clean_chunk = first_chunk.split("]\n")[-1] if "]\n" in first_chunk else first_chunk
            return (
                f"Based on verified agricultural advisories from **{primary_org}** (*{primary_source}*):\n\n"
                f"{clean_chunk[:350]}...\n\n"
                f"Please consult the referenced guide for site-specific agronomic adjustments."
            )

        return "I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation."

    async def reason(
        self,
        question: str,
        rag_context: str,
        sensor_data: Dict[str, Any],
        sources: List[SourceCitation],
        farm_info: str,
        crop: str
    ) -> Dict[str, Any]:
        """
        Executes grounded reasoning with deterministic fact injection and post-generation validation.
        """
        # Ensure structured agricultural context is present
        structured_context = sensor_data.get("structured_agricultural_context")
        if not structured_context:
            structured_context = agricultural_decision_service.evaluate_context(
                crop=crop,
                readings=sensor_data.get("readings", {}),
                retrieved_chunks=[]
            )

        prompt = self._build_prompt(
            question=question,
            rag_context=rag_context,
            sensor_context=sensor_data.get("sensor_context_text", ""),
            farm_info=farm_info,
            structured_context=structured_context
        )

        answer_text = None

        # Check if external LLM provider is configured and available
        if self.provider in ["ollama", "openai", "gemini"] and self.api_base:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    resp = await client.post(
                        f"{self.api_base}/chat/completions",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.2
                        },
                        headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answer_text = data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.info(f"External LLM endpoint unreachable ({e}). Using local grounded reasoning engine.")

        if not answer_text:
            answer_text = self._generate_grounded_local_reasoning(
                question=question,
                rag_context=rag_context,
                sensor_data=sensor_data,
                sources=sources,
                crop=crop,
                structured_context=structured_context
            )

        # 5. POST-GENERATION RESPONSE VALIDATION
        # Validate candidate answer against deterministic calculations to guarantee consistency!
        validated_answer, is_valid, val_log = response_validation_service.validate_and_enforce(
            candidate_response=answer_text,
            structured_context=structured_context
        )

        return {
            "answer": validated_answer,
            "sources": sources,
            "sensor_context": sensor_data,
            "structured_agricultural_context": structured_context,
            "evaluations": structured_context.get("evaluations", {}),
            "computed_status": structured_context.get("computed_status", {}),
            "validation_status": {
                "is_valid": is_valid,
                "log": val_log
            },
            "prompt": prompt
        }

ai_service = AIService()
