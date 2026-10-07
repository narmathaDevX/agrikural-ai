import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("agrikural.decision")

class AgriculturalDecisionService:
    """
    Deterministic Agricultural Decision & Threshold Validation Layer.
    Extracts agronomic thresholds from verified RAG documents and deterministically
    evaluates live IoT sensor metrics against these bounds.
    """

    # Verified University Reference Knowledge Base Thresholds
    # Traceable directly to knowledge_docs/*.txt
    KNOWLEDGE_BASE_THRESHOLDS = {
        "tomato": {
            "source": "TNAU Tomato Cultivation and Irrigation Guide",
            "organization": "Tamil Nadu Agricultural University (TNAU)",
            "soil_moisture": {
                "minimum": 45.0,
                "maximum": 65.0,
                "critical_deficit": 30.0,
                "suboptimal_max": 44.0,
                "excessive": 75.0,
                "unit": "%",
                "notes": "Optimal range 45%-65%. Sub-optimal deficit 30%-44% warrants prompt irrigation."
            },
            "temperature": {
                "minimum": 20.0,
                "maximum": 32.0,
                "critical_max": 35.0,
                "unit": "°C",
                "notes": "Favorable growth 20°C-32°C. Above 35°C impedes pollen viability."
            },
            "humidity": {
                "minimum": 45.0,
                "maximum": 75.0,
                "unit": "%",
                "notes": "Optimal relative humidity 45%-75%."
            },
            "water_level": {
                "minimum": 30.0,
                "maximum": 100.0,
                "critical_deficit": 15.0,
                "unit": "%",
                "notes": "Irrigation reservoir minimum 30%."
            }
        },
        "rice": {
            "source": "ICAR Rice Paddy Water and Nutrient Management",
            "organization": "ICAR - National Rice Research Institute",
            "soil_moisture": {
                "minimum": 55.0,
                "maximum": 90.0,
                "critical_deficit": 40.0,
                "unit": "%",
                "notes": "Lowland rice requires saturated to flooded conditions (55%-90%)."
            },
            "temperature": {
                "minimum": 22.0,
                "maximum": 35.0,
                "unit": "°C",
                "notes": "Optimal growth 22°C-35°C."
            },
            "humidity": {
                "minimum": 60.0,
                "maximum": 90.0,
                "unit": "%",
                "notes": "Favorable relative humidity 60%-90%."
            }
        },
        "chilli": {
            "source": "TNAU Chilli Crop Production Guide",
            "organization": "Tamil Nadu Agricultural University (TNAU)",
            "soil_moisture": {
                "minimum": 50.0,
                "maximum": 65.0,
                "critical_deficit": 35.0,
                "excessive": 75.0,
                "unit": "%",
                "notes": "Soil moisture between 50%-65% promotes maximum flowering and fruit elongation."
            },
            "temperature": {
                "minimum": 20.0,
                "maximum": 34.0,
                "unit": "°C",
                "notes": "Optimal temperature 20°C-34°C."
            }
        },
        "coconut": {
            "source": "KAU Coconut Palm Irrigation and Fertilizer Advisory",
            "organization": "Kerala Agricultural University (KAU) & ICAR-CPCRI",
            "soil_moisture": {
                "minimum": 50.0,
                "maximum": 70.0,
                "critical_deficit": 30.0,
                "unit": "%",
                "notes": "Adult palm requires continuous basin soil moisture conservation."
            },
            "water_level": {
                "minimum": 40.0,
                "unit": "%",
                "notes": "Irrigation buffer minimum 40%."
            }
        }
    }

    def extract_threshold_from_rag_chunks(
        self,
        crop: str,
        parameter: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Dynamically extracts threshold bounds from retrieved RAG document chunks.
        Falls back to verified knowledge base definition if text pattern parsing fails.
        """
        crop_clean = crop.lower().strip()
        doc_source = None

        # Pass 1: Look across all chunks for explicit optimal sensor guidance
        for chk in retrieved_chunks:
            meta = chk.get("metadata", {})
            title = meta.get("title", "")
            text = chk.get("text", "")
            if not doc_source and title:
                doc_source = title

            if parameter == "soil_moisture" and ("soil moisture" in text.lower() or "moisture" in text.lower()):
                m_opt = re.search(r'optimal\s*(?:range)?[:\s\-]+(?:soil\s*moisture\s*)?between\s+(\d+(?:\.\d+)?)\%?\s*(?:and|-|to)\s*(\d+(?:\.\d+)?)\%', text, re.IGNORECASE)
                if not m_opt:
                    m_opt = re.search(r'between\s+(\d+(?:\.\d+)?)\%?\s*(?:and|-|to)\s*(\d+(?:\.\d+)?)\%\s*(?:represents\s*optimal|optimal)', text, re.IGNORECASE)
                if m_opt:
                    min_val = float(m_opt.group(1))
                    max_val = float(m_opt.group(2))
                    return {
                        "minimum": min_val,
                        "maximum": max_val,
                        "unit": "%",
                        "source": doc_source or meta.get("organization", "Agricultural Advisory"),
                        "organization": meta.get("organization", "TNAU / ICAR"),
                        "extracted_from_rag": True
                    }

        # Pass 2: Look for general range definitions if Pass 1 had no explicit optimal label
        for chk in retrieved_chunks:
            meta = chk.get("metadata", {})
            text = chk.get("text", "")
            if parameter == "soil_moisture" and ("soil moisture" in text.lower() or "moisture" in text.lower()):
                m_gen = re.search(r'between\s+(\d+(?:\.\d+)?)\%?\s*(?:and|-|to)\s*(\d+(?:\.\d+)?)\%', text, re.IGNORECASE)
                if m_gen:
                    min_val = float(m_gen.group(1))
                    max_val = float(m_gen.group(2))
                    return {
                        "minimum": min_val,
                        "maximum": max_val,
                        "unit": "%",
                        "source": doc_source or meta.get("organization", "Agricultural Advisory"),
                        "organization": meta.get("organization", "TNAU / ICAR"),
                        "extracted_from_rag": True
                    }

        # Fallback to verified university reference knowledge base
        crop_kb = self.KNOWLEDGE_BASE_THRESHOLDS.get(crop_clean)
        if not crop_kb:
            # Default to tomato reference if crop is general
            crop_kb = self.KNOWLEDGE_BASE_THRESHOLDS["tomato"]

        param_ref = crop_kb.get(parameter)
        if param_ref:
            return {
                **param_ref,
                "source": crop_kb["source"],
                "organization": crop_kb["organization"],
                "extracted_from_rag": False
            }

        return None

    def evaluate_metric(
        self,
        current_value: float,
        minimum: float,
        maximum: float,
        critical_deficit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Deterministic numerical decision:
        - current_value < minimum -> "LOW"
        - current_value > maximum -> "HIGH"
        - minimum <= current_value <= maximum -> "OPTIMAL"
        """
        if current_value < minimum:
            status = "LOW"
            is_critical = critical_deficit is not None and current_value < critical_deficit
            detail = f"Current value ({current_value}) is below the recommended minimum ({minimum})."
        elif current_value > maximum:
            status = "HIGH"
            is_critical = False
            detail = f"Current value ({current_value}) is above the recommended maximum ({maximum})."
        else:
            status = "OPTIMAL"
            is_critical = False
            detail = f"Current value ({current_value}) is within the optimal range ({minimum} - {maximum})."

        return {
            "current": current_value,
            "minimum": minimum,
            "maximum": maximum,
            "status": status,
            "is_critical": is_critical,
            "detail": detail
        }

    def evaluate_context(
        self,
        crop: str,
        readings: Optional[Dict[str, Any]] = None,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None,
        sensor_readings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Builds the complete structured agricultural context containing:
        - Live sensor values
        - Verified agricultural thresholds from RAG
        - Deterministically computed status (LOW, OPTIMAL, HIGH) for each metric
        """
        if readings is None and sensor_readings is not None:
            readings = sensor_readings
        if readings is None:
            readings = {}
        if retrieved_chunks is None:
            retrieved_chunks = []
        crop_clean = crop.lower().strip()
        sensor_map: Dict[str, float] = {}

        # Extract normalized float values from readings dict
        for k, v in readings.items():
            if isinstance(v, dict) and "value" in v and v["value"] is not None:
                try:
                    sensor_map[k] = float(v["value"])
                except (ValueError, TypeError):
                    pass
            elif isinstance(v, (int, float)):
                sensor_map[k] = float(v)

        agricultural_reference: Dict[str, Any] = {}
        computed_status: Dict[str, Any] = {}
        evaluations: Dict[str, Any] = {}

        # Evaluate each active sensor parameter
        for param, val in sensor_map.items():
            # Normalize parameter key
            norm_param = param
            if "soil" in param:
                norm_param = "soil_moisture"
            elif "temp" in param:
                norm_param = "temperature"
            elif "humid" in param:
                norm_param = "humidity"
            elif "water" in param:
                norm_param = "water_level"

            ref = self.extract_threshold_from_rag_chunks(crop_clean, norm_param, retrieved_chunks)
            if ref and "minimum" in ref and "maximum" in ref:
                eval_res = self.evaluate_metric(
                    current_value=val,
                    minimum=ref["minimum"],
                    maximum=ref["maximum"],
                    critical_deficit=ref.get("critical_deficit")
                )
                agricultural_reference[norm_param] = {
                    "minimum": ref["minimum"],
                    "maximum": ref["maximum"],
                    "unit": ref.get("unit", ""),
                    "source": ref["source"],
                    "organization": ref.get("organization", ""),
                    "notes": ref.get("notes", "")
                }
                computed_status[norm_param] = eval_res["status"]
                r_meta = readings.get(param) or readings.get(norm_param)
                if isinstance(r_meta, dict):
                    sensor_id_val = r_meta.get("sensor_id")
                    timestamp_val = r_meta.get("timestamp")
                    is_stale_val = r_meta.get("is_stale", False)
                    last_updated_text_val = r_meta.get("last_updated_text")
                else:
                    sensor_id_val = None
                    timestamp_val = None
                    is_stale_val = False
                    last_updated_text_val = None

                evaluations[norm_param] = {
                    **eval_res,
                    "unit": ref.get("unit", ""),
                    "source": ref["source"],
                    "source_document": ref["source"],
                    "organization": ref.get("organization", ""),
                    "sensor_id": sensor_id_val,
                    "timestamp": timestamp_val,
                    "is_stale": is_stale_val,
                    "last_updated_text": last_updated_text_val
                }

        return {
            "crop": crop,
            "sensor": sensor_map,
            "agricultural_reference": agricultural_reference,
            "computed_status": computed_status,
            "evaluations": evaluations
        }

agricultural_decision_service = AgriculturalDecisionService()
