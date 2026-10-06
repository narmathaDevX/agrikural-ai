import re
from typing import Tuple

def detect_language(text: str) -> Tuple[str, float]:
    """
    Detects whether the input text is Tamil ('ta'), Malayalam ('ml'), or English ('en').
    Returns (language_code, confidence).
    
    Uses Unicode script range heuristics:
    - Tamil: \u0B80 - \u0BFF
    - Malayalam: \u0D00 - \u0D7F
    - English/Latin: ASCII letters
    """
    if not text or not text.strip():
        return "en", 0.5

    clean_text = text.strip()
    total_chars = len(clean_text)

    # Count script characters
    tamil_chars = len(re.findall(r'[\u0B80-\u0BFF]', clean_text))
    malayalam_chars = len(re.findall(r'[\u0D00-\u0D7F]', clean_text))
    latin_chars = len(re.findall(r'[A-Za-z]', clean_text))

    if tamil_chars > malayalam_chars and tamil_chars > 0:
        ratio = tamil_chars / max(1, (tamil_chars + malayalam_chars + latin_chars))
        confidence = min(0.99, max(0.70, ratio))
        return "ta", float(confidence)

    if malayalam_chars > tamil_chars and malayalam_chars > 0:
        ratio = malayalam_chars / max(1, (tamil_chars + malayalam_chars + latin_chars))
        confidence = min(0.99, max(0.70, ratio))
        return "ml", float(confidence)

    if latin_chars > 0:
        return "en", 0.95

    return "en", 0.80

def get_language_display_name(code: str) -> str:
    mapping = {
        "ta": "Tamil (தமிழ்)",
        "ml": "Malayalam (മലയാളം)",
        "en": "English",
    }
    return mapping.get(code.lower(), "English")
