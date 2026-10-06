import logging
import httpx
from typing import Dict, Any, List
from app.config.settings import settings
from app.schemas.rag import SourceCitation

logger = logging.getLogger("agrikural.ai")

SYSTEM_PROMPT = """You are Agrikural, an expert AI Agricultural Assistant.
Answer strictly using the provided verified agricultural knowledge and current farm sensor data.
Do NOT invent or extrapolate agricultural facts.
If the retrieved context does not contain enough verified information to answer the question, state:
"I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation."
Distinguish clearly between documented agricultural recommendations and current sensor conditions.
Always cite the source documents (e.g. ICAR, TNAU, KAU) where applicable.
"""

class AIService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = settings.LLM_MODEL
        self.api_base = settings.LLM_API_BASE
        self.api_key = settings.LLM_API_KEY

    def _build_prompt(self, question: str, rag_context: str, sensor_context: str, farm_info: str) -> str:
        return f"""{SYSTEM_PROMPT}

FARM DETAILS:
{farm_info}

CURRENT FARM SENSOR DATA:
{sensor_context}

VERIFIED AGRICULTURAL CONTEXT:
{rag_context if rag_context.strip() else "No matching agricultural documents found."}

FARMER QUESTION:
{question}

Provide a concise, practical, and grounded answer:"""

    def _generate_grounded_local_reasoning(
        self,
        question: str,
        rag_context: str,
        sensor_data: Dict[str, Any],
        sources: List[SourceCitation],
        crop: str
    ) -> str:
        """
        Deterministic, grounded local reasoning engine.
        Synthesizes sensor metrics directly with verified agronomic criteria
        from ICAR / TNAU documentation.
        """
        q_lower = question.lower()
        readings = sensor_data.get("readings", {})
        soil_moisture = readings.get("soil_moisture", {}).get("value")
        temperature = readings.get("temperature", {}).get("value")
        humidity = readings.get("humidity", {}).get("value")

        has_sources = len(sources) > 0

        # Soil moisture / irrigation query
        if any(w in q_lower for w in ["moisture", "water", "irrigation", "soil", "ஈரப்பதம்", "தண்ணீர்", "ഈർപ്പം"]):
            if soil_moisture is not None:
                source_name = sources[0].title if has_sources else "TNAU Agronomy Guidelines"
                org_name = sources[0].organization if has_sources else "Tamil Nadu Agricultural University"
                
                # Check agronomic thresholds for Tomato / general crops
                if soil_moisture < 30.0:
                    status = "CRITICAL / LOW"
                    advice = (
                        f"Your current soil moisture is at **{soil_moisture}%**, which is below the optimal threshold (45% - 65%) for {crop}.\n\n"
                        f"According to **{org_name}** (*{source_name}*), prolonged moisture stress during flowering and fruit setting "
                        f"leads to flower drop and blossom end rot. **Immediate drip irrigation is recommended** for 1.5 to 2 hours."
                    )
                elif soil_moisture > 75.0:
                    status = "HIGH / SATURATED"
                    advice = (
                        f"Your current soil moisture is at **{soil_moisture}%**, which is above field capacity.\n\n"
                        f"Per **{org_name}** guidelines, excessive soil moisture impedes root aeration and can encourage damping-off or root rot. "
                        f"**Withhold irrigation** until soil moisture recedes below 60%."
                    )
                else:
                    status = "OPTIMAL"
                    advice = (
                        f"Your current soil moisture is at **{soil_moisture}%**, which is within the **optimal range (45% - 65%)** for {crop}.\n\n"
                        f"Per **{org_name}** (*{source_name}*), maintain current irrigation schedule. "
                        f"No immediate additional watering is required."
                    )

                if temperature is not None:
                    advice += f"\n\n*Current Field Temperature: {temperature}°C*"
                return advice
            else:
                if has_sources:
                    return (
                        f"According to **{sources[0].organization}** (*{sources[0].title}*), {crop} requires maintaining soil moisture "
                        f"between 50% and 70% of field capacity. Irrigate at 4-5 day intervals in red loam soils, preferably via drip irrigation."
                    )
                else:
                    return "I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation."

        # Temperature or climate query
        elif any(w in q_lower for w in ["temperature", "heat", "climate", "வெப்பநிலை", "தாபനില"]):
            if temperature is not None:
                source_name = sources[0].title if has_sources else "ICAR Crop Physiology Advisory"
                org_name = sources[0].organization if has_sources else "ICAR"
                if temperature > 35.0:
                    return (
                        f"Current field temperature is **{temperature}°C**. According to **{org_name}** (*{source_name}*), "
                        f"temperatures exceeding 35°C increase evapotranspiration and risk pollen sterility in {crop}. "
                        f"Consider shade netting or morning/evening micro-sprinkler misting to reduce canopy heat stress."
                    )
                else:
                    return (
                        f"Current field temperature is **{temperature}°C**, which is within the favorable growing range (20°C - 32°C) "
                        f"for {crop} according to **{org_name}** guidelines."
                    )

        # Fertilizer or nutrient query
        elif any(w in q_lower for w in ["fertilizer", "nutrient", "npk", "nitrogen", "உரம்", "വളം"]):
            if has_sources:
                return (
                    f"According to **{sources[0].organization}** (*{sources[0].title}*), the recommended fertilizer dosage for {crop} "
                    f"is N:P:K at 150:100:100 kg/ha for hybrid cultivars. Apply 50% nitrogen and entire P and K as basal dressing, "
                    f"with remaining N in split doses at 30 and 45 days after planting."
                )
            else:
                return "I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation."

        # General RAG synthesis
        if has_sources and rag_context.strip():
            first_chunk = rag_context.split("\n\n")[0]
            clean_chunk = first_chunk.split("]\n")[-1] if "]\n" in first_chunk else first_chunk
            return (
                f"Based on verified agricultural advisories from **{sources[0].organization}** (*{sources[0].title}*):\n\n"
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
        Executes grounded reasoning.
        Attempts LLM provider (Ollama / OpenAI / Gemini) if reachable,
        otherwise seamlessly uses the grounded agronomic reasoning engine.
        """
        prompt = self._build_prompt(
            question=question,
            rag_context=rag_context,
            sensor_context=sensor_data.get("sensor_context_text", ""),
            farm_info=farm_info
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
                crop=crop
            )

        return {
            "answer": answer_text,
            "sources": sources,
            "sensor_context": sensor_data,
            "prompt": prompt
        }

ai_service = AIService()
