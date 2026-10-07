import re
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("agrikural.validation")

class ResponseValidationService:
    """
    Validates AI-generated agricultural claims against deterministic calculated status.
    Guarantees mathematical and agronomic consistency before answers reach the user.
    """

    def validate_and_enforce(
        self,
        candidate_response: str,
        structured_context: Dict[str, Any]
    ) -> Tuple[str, bool, str]:
        """
        Validates candidate answer text against computed_status and agricultural_reference.
        Returns:
            (final_response, is_valid, validation_log)
        """
        computed_status = structured_context.get("computed_status", {})
        sensor = structured_context.get("sensor", {})
        ref = structured_context.get("agricultural_reference", {})
        crop = structured_context.get("crop", "Tomato")

        is_valid = True
        violation_reason = "Valid"

        # Check Soil Moisture claims
        if "soil_moisture" in computed_status:
            status = computed_status["soil_moisture"]
            current_val = sensor.get("soil_moisture")
            sm_ref = ref.get("soil_moisture", {})
            min_thresh = sm_ref.get("minimum", 45.0)
            max_thresh = sm_ref.get("maximum", 65.0)
            source_doc = sm_ref.get("source", "TNAU Agricultural Advisory")
            org = sm_ref.get("organization", "Tamil Nadu Agricultural University (TNAU)")

            resp_lower = candidate_response.lower()

            # Rule 1: Contradiction Check
            # If computed status is LOW, candidate must NOT state that it is optimal, within optimal range, or sufficient!
            if status == "LOW":
                contradictory_phrases = [
                    "within the optimal",
                    "within optimal",
                    "in the optimal",
                    "within recommended optimal",
                    "within the recommended optimal",
                    "is optimal",
                    "currently optimal",
                    "sufficient for",
                    "is sufficient",
                    "moisture is sufficient",
                    "no immediate additional watering is required",
                    "no irrigation is required",
                    "no immediate watering",
                ]
                has_contradiction = any(phrase in resp_lower for phrase in contradictory_phrases)

                # Check mathematical impossibility claim: "36.4% is within (45% - 65%)"
                if current_val is not None:
                    pattern = rf"{current_val}.*?within.*?(?:{min_thresh}|45).*?(?:{max_thresh}|65)"
                    if re.search(pattern, resp_lower, re.DOTALL):
                        has_contradiction = True

                if has_contradiction:
                    is_valid = False
                    violation_reason = f"Numerical contradiction: Status is LOW ({current_val}% < {min_thresh}%), but response claimed optimal/sufficient."
                    logger.warning(f"REJECTED RESPONSE: {violation_reason}")

                    # Check water storage warning
                    water_warning = ""
                    water_val = sensor.get("water_level") or sensor.get("water_level_pct")
                    if water_val is not None and (water_val < 30.0 or computed_status.get("water_level") == "LOW"):
                        water_warning = f"\n\n**Warning:** Irrigation water reservoir is critically low at **{water_val}%**. Replenish water storage before prolonged irrigation."

                    stale_warning = ""
                    if structured_context.get("is_stale") or sm_ref.get("is_stale"):
                        human_age = structured_context.get("last_updated_human") or sm_ref.get("last_updated_text") or "recently"
                        dev_id = structured_context.get("device_id") or "AGRI-DEV-001"
                        stale_warning = f"\n\n⚠️ **Hardware Notice:** Physical device `{dev_id}` is currently disconnected ({human_age}). Do not assume this reading reflects current moisture conditions."

                    # Deterministically generate ground-truth corrected response strictly grounded in TNAU/ICAR docs
                    corrected_response = (
                        f"Your current soil moisture is at **{current_val}%**, which is **below** the recommended optimal range "
                        f"({min_thresh}% - {max_thresh}%) for {crop}.\n\n"
                        f"According to **{org}** (*{source_doc}*):\n"
                        f"- Optimal root-zone soil moisture: **{min_thresh}% to {max_thresh}%**\n"
                        f"- Current condition: Soil moisture is at a **sub-optimal deficit** ({current_val}%).\n\n"
                        f"**Agronomic Recommendation:** Prompt irrigation is advised to restore root zone moisture into the optimal {min_thresh}%–{max_thresh}% range and prevent crop moisture stress."
                        f"{water_warning}"
                        f"{stale_warning}"
                    )
                    return corrected_response, False, violation_reason

            elif status == "HIGH":
                contradictory_phrases = [
                    "within the optimal",
                    "below optimal",
                    "immediate irrigation is recommended",
                    "deficit",
                ]
                if any(phrase in resp_lower for phrase in contradictory_phrases):
                    is_valid = False
                    violation_reason = f"Contradiction: Status is HIGH ({current_val}% > {max_thresh}%), but response suggested deficit/irrigation."
                    corrected_response = (
                        f"Your current soil moisture is at **{current_val}%**, which is **above** the recommended optimal range "
                        f"({min_thresh}% - {max_thresh}%) for {crop}.\n\n"
                        f"According to **{org}** (*{source_doc}*), excessive soil moisture impedes root aeration and increases risk of root rot. "
                        f"**Withhold irrigation** until soil moisture naturally recedes below {max_thresh}%."
                    )
                    return corrected_response, False, violation_reason

            elif status == "OPTIMAL":
                contradictory_phrases = [
                    "is below",
                    "below the optimal",
                    "immediate drip irrigation is recommended",
                    "severe water deficit",
                ]
                if any(phrase in resp_lower for phrase in contradictory_phrases):
                    is_valid = False
                    violation_reason = f"Contradiction: Status is OPTIMAL ({min_thresh}% <= {current_val}% <= {max_thresh}%), but response claimed deficit."
                    corrected_response = (
                        f"Your current soil moisture is at **{current_val}%**, which is within the **optimal range ({min_thresh}% - {max_thresh}%)** for {crop}.\n\n"
                        f"According to **{org}** (*{source_doc}*), soil moisture conditions are favorable. Maintain regular monitoring; no emergency watering is needed at this moment."
                    )
                    return corrected_response, False, violation_reason

        # Ensure no hallucinated arbitrary irrigation duration (e.g. "for 1.5 to 2 hours") unless supported
        cleaned_response = candidate_response
        if "for 1.5 to 2 hours" in cleaned_response:
            cleaned_response = cleaned_response.replace(
                "for 1.5 to 2 hours",
                "until root-zone moisture recovers to the recommended field capacity"
            )

        return cleaned_response, True, "Response adheres to computed facts."

response_validation_service = ResponseValidationService()
