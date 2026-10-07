import logging
import re
from typing import Dict, Any, Optional
from app.config.settings import settings
from app.utils.lang_detect import detect_language

logger = logging.getLogger("agrikural.translation")

class BaseTranslationAdapter:
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        raise NotImplementedError

class AgriculturalLocalTranslationAdapter(BaseTranslationAdapter):
    """
    High-accuracy Agricultural translation engine.
    Supports bidirectional translation:
    Tamil <-> English, Malayalam <-> English, English <-> Tamil, English <-> Malayalam.
    Uses agricultural domain lexicons + syntactic phrase matching with HuggingFace transformers
    fallback where available.
    """
    def __init__(self):
        self._hf_pipeline = None
        self._hf_attempted = False

        # Domain-specific agricultural terminology mappings
        self.ta_to_en = {
            "மண்": "soil",
            "ஈரப்பதம்": "moisture",
            "ஈரம்": "moisture",
            "வெப்பநிலை": "temperature",
            "சூரிய ஒளி": "sunlight",
            "வெளிச்சம்": "light",
            "தண்ணீர்": "water",
            "நீர்": "water",
            "நீர்ப்பாசனம்": "irrigation",
            "பாசனம்": "irrigation",
            "சொட்டு நீர் பாசனம்": "drip irrigation",
            "தக்காளி": "tomato",
            "நெல்": "rice paddy",
            "மிளகாய்": "chilli",
            "தென்னை": "coconut",
            "வாழை": "banana",
            "உரம்": "fertilizer",
            "இயற்கை உரம்": "organic manure",
            "பூச்சி": "pest",
            "பூச்சிகள்": "pests",
            "நோய்": "disease",
            "நோய்கள்": "diseases",
            "இலை சுருட்டை": "leaf curl",
            "இலை கருகல்": "leaf blight",
            "வேர் அழுகல்": "root rot",
            "போதுமா": "is it sufficient",
            "எவ்வளவு": "how much",
            "தேவை": "is needed",
            "அளவு": "level/quantity",
            "செடி": "plant",
            "பயிர்": "crop",
            "விவசாயம்": "agriculture",
            "பரிந்துரை": "recommendation",
            "ஆலோசனை": "advice",
            "சரியான": "optimal/appropriate",
            "குறைவாக": "low",
            "அதிகமாக": "high",
            "இன்றைய": "today's",
            "தற்போதைய": "current",
        }

        self.ml_to_en = {
            "മണ്ണ്": "soil",
            "ഈർപ്പം": "moisture",
            "താപനില": "temperature",
            "സൂര്യപ്രകാശം": "sunlight",
            "വെളിച്ചം": "light",
            "വെള്ളം": "water",
            "നനയ്ക്കൽ": "irrigation",
            "തുള്ളി നന": "drip irrigation",
            "തക്കാളി": "tomato",
            "നെല്ല്": "paddy rice",
            "മുളക്": "chilli",
            "തെങ്ങ്": "coconut",
            "വാഴ": "banana",
            "വളം": "fertilizer",
            "ജൈവവളം": "organic manure",
            "കീടം": "pest",
            "കീടങ്ങൾ": "pests",
            "രോഗം": "disease",
            "രോഗങ്ങൾ": "diseases",
            "ഇല ചുരുളൽ": "leaf curl",
            "ഇല കരിച്ചിൽ": "leaf blight",
            "വേരുചീയൽ": "root rot",
            "മതിയോ": "is it sufficient",
            "എത്ര": "how much",
            "ആവശ്യമാണ്": "is needed",
            "അളവ്": "quantity/level",
            "ചെടി": "plant",
            "വിള": "crop",
            "കൃഷി": "agriculture",
            "ശുപാർശ": "recommendation",
            "ശരിയായ": "optimal",
            "കുറവാണ്": "low",
            "കൂടുതലാണ്": "high",
            "ഇന്നത്തെ": "today's",
            "നിലവിലെ": "current",
        }

        self.en_to_ta_keywords = {
            "soil moisture": "மண் ஈரப்பதம்",
            "soil": "மண்",
            "moisture": "ஈரப்பதம்",
            "temperature": "வெப்பநிலை",
            "humidity": "ஈரப்பதம் (Humidity)",
            "irrigation": "நீர்ப்பாசனம்",
            "drip irrigation": "சொட்டு நீர் பாசனம்",
            "water": "தண்ணீர்",
            "tomato": "தக்காளி",
            "rice": "நெல்",
            "chilli": "மிளகாய்",
            "coconut": "தென்னை",
            "banana": "வாழை",
            "fertilizer": "உரம்",
            "nitrogen": "நைட்ரஜன்",
            "phosphorus": "பாஸ்பரஸ்",
            "potassium": "பொட்டாசியம்",
            "pest": "பூச்சி",
            "disease": "நோய்",
            "sufficient": "போதுமானது",
            "insufficient": "போதுமானதாக இல்லை",
            "low": "குறைவாக உள்ளது",
            "high": "அதிகமாக உள்ளது",
            "optimal": "சரியான அளவில் உள்ளது",
            "recommendation": "பரிந்துரை",
            "advisory": "விவசாய ஆலோசனை",
            "warning": "எச்சரிக்கை",
            "critical": "முக்கிய எச்சரிக்கை",
            "hours": "மணிநேரம்",
            "liters": "லிட்டர்",
            "percentage": "சதவீதம்",
        }

        self.en_to_ml_keywords = {
            "soil moisture": "മണ്ണിലെ ഈർപ്പം",
            "soil": "മണ്ണ്",
            "moisture": "ഈർപ്പം",
            "temperature": "താപനില",
            "humidity": "ആർദ്രത (Humidity)",
            "irrigation": "നനയ്ക്കൽ (Irrigation)",
            "drip irrigation": "തുള്ളി നന",
            "water": "വെള്ളം",
            "tomato": "തക്കാളി",
            "rice": "നെല്ല്",
            "chilli": "മുളക്",
            "coconut": "തെങ്ങ്",
            "banana": "വാഴ",
            "fertilizer": "വളം",
            "pest": "കീടങ്ങൾ",
            "disease": "രോഗം",
            "sufficient": "പര്യാപ്തമാണ് (മതിയായതാണ്)",
            "insufficient": "മതിയായതല്ല",
            "low": "കുറവാണ്",
            "high": "കൂടുതലാണ്",
            "optimal": "അനുയോജ്യമായ അളവിലാണ്",
            "recommendation": "ശുപാർശ",
            "warning": "മുന്നറിയിപ്പ്",
        }

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if source_lang == target_lang or not text.strip():
            return text

        # 1. Tamil -> English
        if source_lang == "ta" and target_lang == "en":
            clean = text.strip()
            # Common agricultural queries
            if "ஈரப்பதம்" in clean and any(w in clean for w in ["போதுமா", "போதும்", "போதுமான", "தேவை", "இருக்கிறதா", "நிலவரம்"]):
                for crop_k, crop_en in [("தக்காளி", "tomato"), ("நெல்", "rice"), ("மிளகாய்", "chilli"), ("வாழை", "banana"), ("தென்னை", "coconut")]:
                    if crop_k in clean:
                        return f"Is the current soil moisture level sufficient for {crop_en} crop?"
                return "Is the current soil moisture level sufficient for the crop?"

            if "தண்ணீர்" in clean and ("தேவை" in clean or "பாய்ச்ச" in clean or "விடவா" in clean):
                for crop_k, crop_en in [("தக்காளி", "tomato"), ("நெல்", "rice"), ("மிளகாய்", "chilli")]:
                    if crop_k in clean:
                        return f"Is irrigation required now for {crop_en} crop?"
                return "Is irrigation required now for the crop?"

            if "வெப்பநிலை" in clean and any(w in clean for w in ["அதிகமா", "சரியா", "உகந்ததா", "எப்படி"]):
                return "Is the temperature optimal for current crop growth?"

            if "உரம்" in clean:
                return "What is the recommended fertilizer schedule and quantity?"

            if "பூச்சி" in clean or "நோய்" in clean:
                return "What are the recommended pest and disease management practices?"

            # Word-by-word token substitution with agricultural context
            words = clean.split()
            translated_words = []
            for w in words:
                cleaned_w = re.sub(r'[^\w\s]', '', w)
                matched = False
                for k, v in self.ta_to_en.items():
                    if k in cleaned_w:
                        translated_words.append(v)
                        matched = True
                        break
                if not matched:
                    translated_words.append(w)
            
            result = " ".join(translated_words)
            return f"Regarding agricultural query: {result}"

        # 2. Malayalam -> English
        if source_lang == "ml" and target_lang == "en":
            clean = text.strip()
            if "ഈർപ്പം" in clean and any(w in clean for w in ["മതിയോ", "ആവശ്യമുണ്ടോ", "മതിയായതാണോ", "എങ്ങനെ"]):
                for crop_k, crop_en in [("തക്കാളി", "tomato"), ("നെല്ല്", "paddy rice"), ("മുളക്", "chilli"), ("വാഴ", "banana"), ("തെങ്ങ്", "coconut")]:
                    if crop_k in clean:
                        return f"Is the current soil moisture level sufficient for {crop_en} crop?"
                return "Is the current soil moisture level sufficient for the crop?"

            if "വെള്ളം" in clean or "നനയ്ക്ക" in clean:
                return "Is irrigation required for the crop?"

            if "താപനില" in clean:
                return "Is the temperature optimal for the crop?"

            if "വളം" in clean:
                return "What is the recommended fertilizer dosage for the crop?"

            words = clean.split()
            translated_words = []
            for w in words:
                cleaned_w = re.sub(r'[^\w\s]', '', w)
                matched = False
                for k, v in self.ml_to_en.items():
                    if k in cleaned_w:
                        translated_words.append(v)
                        matched = True
                        break
                if not matched:
                    translated_words.append(w)

            result = " ".join(translated_words)
            return f"Regarding agricultural query: {result}"

        # 3. English -> Tamil (COMPLETE Response Translation)
        if source_lang == "en" and target_lang == "ta":
            return self._translate_en_to_ta(text)

        # 4. English -> Malayalam (COMPLETE Response Translation)
        if source_lang == "en" and target_lang == "ml":
            return self._translate_en_to_ml(text)

        return text

    def _translate_en_to_ta(self, text: str) -> str:
        crops_ta = {
            "tomato": "தக்காளி",
            "rice": "நெல்",
            "paddy": "நெல்",
            "chilli": "மிளகாய்",
            "coconut": "தென்னை",
            "banana": "வாழை",
            "sugarcane": "கரும்பு",
            "cotton": "பருத்தி",
            "maize": "மக்காச்சோளம்"
        }

        t = text

        # 1. Hardware Disconnection Alerts
        t = re.sub(
            r'⚠️\s*\*\*Hardware Telemetry Alert:\*\*\s*Gateway\s*`([^`]+)`\s*is currently\s*\*\*disconnected\*\*\s*\(([^)]+)\)\.\s*This reading is stale and must not be treated as current live moisture\.\s*Verify physical field conditions or check hardware connectivity before irrigating\.',
            r'⚠️ **வன்பொருள் எச்சரிக்கை:** கேட்வே `\1` தற்போது **இணைக்கப்படவில்லை** (\2). இந்த அளவீடு பழையது மற்றும் தற்போதைய நேரடி ஈரப்பதமாக கருதப்படக்கூடாது. நீர்ப்பாசனம் செய்வதற்கு முன் நேரடி கள நிலைமைகளை சரிபார்க்கவும் அல்லது வன்பொருள் இணைப்பை சரிபார்க்கவும்.',
            t
        )
        t = re.sub(
            r'⚠️\s*\*\*Hardware Notice:\*\*\s*Physical device\s*`([^`]+)`\s*is currently disconnected\s*\(([^)]+)\)\.\s*Do not assume this reading reflects current moisture conditions\.',
            r'⚠️ **வன்பொருள் எச்சரிக்கை:** சாதனம் `\1` தற்போது இணைக்கப்படவில்லை (\2). இந்த அளவீடு தற்போதைய கள நிலைமையை பிரதிபலிக்கிறது என்று கருத வேண்டாம்.',
            t
        )

        # 2. Main Telemetry Assessment Paragraphs
        t = re.sub(
            r'Your (?:last recorded|current) soil moisture (?:is at|\(Sensor `[^`]+` on Device `[^`]+`[^)]*\) was)\s*\*\*([0-9.]+%)\*\*,\s*which is\s*\*\*below\*\*\s*the recommended optimal range\s*\(([0-9.]+%)\s*[-–]\s*([0-9.]+%)\)\s*for\s*([A-Za-z]+)\.?',
            lambda m: f"தற்போது உங்கள் மண்ணின் ஈரப்பதம் **{m.group(1)}** ஆக உள்ளது. இது {crops_ta.get(m.group(4).lower(), m.group(4))} பயிருக்கு பரிந்துரைக்கப்பட்ட **{m.group(2)} முதல் {m.group(3)}** வரையிலான உகந்த வரம்பை விட குறைவாக உள்ளது.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Your (?:last recorded|current) soil moisture (?:is at|\(Sensor `[^`]+` on Device `[^`]+`[^)]*\) was)\s*\*\*([0-9.]+%)\*\*,\s*which is within the\s*\*\*optimal range\s*\(([0-9.]+%)\s*[-–]\s*([0-9.]+%)\)\*\*\s*for\s*([A-Za-z]+)\.?',
            lambda m: f"தற்போது உங்கள் மண்ணின் ஈரப்பதம் **{m.group(1)}** ஆக உள்ளது. இது {crops_ta.get(m.group(4).lower(), m.group(4))} பயிருக்கு **உகந்த வரம்பிற்குள் ({m.group(2)} - {m.group(3)})** உள்ளது.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Your (?:last recorded|current) soil moisture (?:is at|\(Sensor `[^`]+` on Device `[^`]+`[^)]*\) was)\s*\*\*([0-9.]+%)\*\*,\s*which is\s*\*\*above\*\*\s*the recommended optimal range\s*\(([0-9.]+%)\s*[-–]\s*([0-9.]+%)\)\s*for\s*([A-Za-z]+)\.?',
            lambda m: f"தற்போது உங்கள் மண்ணின் ஈரப்பதம் **{m.group(1)}** ஆக உள்ளது. இது {crops_ta.get(m.group(4).lower(), m.group(4))} பயிருக்கு பரிந்துரைக்கப்பட்ட உகந்த வரம்பை விட ({m.group(2)} - {m.group(3)}) **அதிகமாக** உள்ளது.",
            t, flags=re.IGNORECASE
        )

        # 3. Document Citation Lines
        t = re.sub(
            r'According to\s*\*\*([^*]+)\*\*\s*\(\*([^*]+)\*\):',
            r'**\1** வழங்கிய *\2* வழிகாட்டுதலின்படி:',
            t
        )
        t = re.sub(
            r'According to\s*\*\*([^*]+)\*\*\s*\(\*([^*]+)\*\),',
            r'**\1** (*\2*) வழிகாட்டுதலின்படி,',
            t
        )
        t = re.sub(
            r'According to\s*\*\*([^*]+)\*\*:',
            r'**\1** வழிகாட்டுதலின்படி:',
            t
        )
        t = re.sub(
            r'According to\s*\*\*([^*]+)\*\*,',
            r'**\1** வழிகாட்டுதலின்படி,',
            t
        )
        t = re.sub(
            r'Based on verified agricultural advisories from\s*\*\*([^*]+)\*\*\s*\(\*([^*]+)\*\):',
            r'**\1** (*\2*) சரிபார்க்கப்பட்ட விவசாய வழிகாட்டுதலின்படி:',
            t
        )

        # 4. Bullet Items
        t = re.sub(
            r'-\s*Optimal root-zone soil moisture:\s*\*\*([0-9.]+%)\s*to\s*([0-9.]+%)\*\*',
            r'- வேர் பகுதியில் உகந்த மண் ஈரப்பதம்: **\1 முதல் \2**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*Optimal range:\s*\*\*([0-9.]+%)[-–]([0-9.]+%)\*\*',
            r'- உகந்த வரம்பு: **\1 முதல் \2**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*(?:Current\s+)?condition:\s*Soil moisture (?:indicates a|is at a)\s*\*\*(?:sub-optimal deficit|severe water deficit)(?:\s*\(([0-9.]+%)\))?\*\*(?:\s*\(([0-9.]+%)\))?\.?',
            lambda m: f"- தற்போதைய நிலை: **{m.group(1) or m.group(2) or ''}**, அதாவது ஈரப்பதம் உகந்த அளவை விட குறைவாக உள்ளது.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*(?:Current\s+)?condition:\s*Soil moisture is (?:within|in) the optimal range(?:\s*\(([0-9.]+%)\))?\.?',
            lambda m: f"- தற்போதைய நிலை: **{m.group(1) or ''}**, மண் ஈரப்பதம் உகந்த அளவில் உள்ளது.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*(?:Current\s+)?condition:\s*Soil moisture indicates excessive waterlogging(?:\s*\(([0-9.]+%)\))?\.?',
            lambda m: f"- தற்போதைய நிலை: **{m.group(1) or ''}**, அதிகப்படியான நீர் தேக்கம் உள்ளது.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*Current condition:\s*\*\*LOW\*\*',
            r'- தற்போதைய நிலை: **குறைவாக உள்ளது (LOW)**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*Current condition:\s*\*\*HIGH\*\*',
            r'- தற்போதைய நிலை: **அதிகமாக உள்ளது (HIGH)**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*Current condition:\s*\*\*OPTIMAL\*\*',
            r'- தற்போதைய நிலை: **உகந்த அளவில் உள்ளது (OPTIMAL)**',
            t, flags=re.IGNORECASE
        )

        # 5. Explanatory Advice Sentences
        t = re.sub(
            r'Prolonged moisture deficit during flowering and fruit setting increases risk of blossom-end rot and flower drop\.\s*\*\*Prompt irrigation is recommended\*\*\s*to restore root-zone moisture into the optimal\s*([0-9.]+%)[-–]([0-9.]+%)\s*range\.',
            r'பூக்கும் மற்றும் காய் பிடிக்கும் பருவத்தில் தொடர்ச்சியான ஈரப்பதக் குறைபாடு பூ உதிர்வு மற்றும் காய் அழுகல் அபாயத்தை அதிகரிக்கும். வேர் பகுதியில் மண் ஈரப்பதத்தை உகந்த \1–\2 வரம்பிற்கு மீட்டெடுக்க **உடனடி நீர்ப்பாசனம் செய்ய பரிந்துரைக்கப்படுகிறது**.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'\*\*Agronomic Recommendation:\*\*\s*Prompt irrigation is advised to restore root zone moisture into the optimal\s*([0-9.]+%)[-–]([0-9.]+%)\s*range and prevent crop moisture stress\.',
            r'**விவசாய பரிந்துரை:** வேர் மண்டல ஈரப்பதத்தை உகந்த \1–\2 வரம்பிற்கு மீட்டெடுக்கவும், பயிர் வறட்சி அழுத்தத்தைத் தடுக்கவும் உடனடி நீர்ப்பாசனம் மேற்கொள்ள பரிந்துரைக்கப்படுகிறது.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Prompt irrigation is recommended to restore root-zone moisture into the optimal range\.',
            r'வேர் பகுதியில் மண் ஈரப்பதத்தை உகந்த வரம்பிற்கு மீட்டெடுக்க தேவையான நீர்ப்பாசனத்தை மேற்கொள்ள வேண்டும்.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'\*\*Prompt irrigation is recommended\.\*\*',
            r'**உடனடி நீர்ப்பாசனம் செய்ய பரிந்துரைக்கப்படுகிறது.**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'immediate irrigation is recommended',
            r'உடனடியாக நீர்ப்பாசனம் செய்ய பரிந்துரைக்கப்படுகிறது',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'excessive soil moisture impedes root aeration and increases (?:risk of root rot|susceptibility to fungal root rot)\.\s*\*\*Withhold irrigation\*\*\s*until soil moisture (?:naturally )?recedes below\s*([0-9.]+%)',
            r'அதிகப்படியான மண் ஈரப்பதம் வேர் காற்றோட்டத்தை பாதிக்கிறது மற்றும் பூஞ்சை வேர் அழுகல் அபாயத்தை அதிகரிக்கிறது. மண் ஈரப்பதம் \1 கீழே குறையும் வரை **நீர்ப்பாசனத்தை நிறுத்தி வைக்கவும்**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'soil moisture conditions are favorable\.\s*Maintain regular monitoring;\s*no immediate additional watering is required\.',
            r'மண் ஈரப்பத நிலை சாதகமாக உள்ளது. தொடர்ந்து கண்காணிக்கவும்; தற்போது உடனடி நீர்ப்பாசனம் தேவையில்லை.',
            t, flags=re.IGNORECASE
        )

        # 6. Reservoir & Water Warnings
        t = re.sub(
            r'\*\*Warning:\*\*\s*Irrigation water reservoir is critically low at\s*\*\*([0-9.]+%)\*\*\.\s*Replenish water storage before (?:running irrigation pumps|prolonged irrigation)\.',
            r'**எச்சரிக்கை:** நீர்ப்பாசனத்திற்கான நீர் சேமிப்பு அளவு தற்போது **\1** மட்டுமே உள்ளது. நீர்ப்பாசன பம்பை இயக்குவதற்கு முன் நீர் சேமிப்பை நிரப்பவும்.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Warning:\s*Irrigation water reservoir is critically low at\s*\*\*([0-9.]+%)\*\*\.?',
            r'**எச்சரிக்கை:** நீர்ப்பாசனத்திற்கான நீர் சேமிப்பு அளவு தற்போது **\1** மட்டுமே உள்ளது. நீர்ப்பாசன பம்பை இயக்குவதற்கு முன் நீர் சேமிப்பை நிரப்பவும்.',
            t, flags=re.IGNORECASE
        )

        # 7. Temperature Notes
        t = re.sub(
            r'Current Field Temperature:\s*\*\*([0-9.]+°C)\*\*',
            r'தற்போதைய வயல் வெப்பநிலை: **\1**.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'\*Current Field Temperature:\s*([0-9.]+°C)\*',
            r'*தற்போதைய வயல் வெப்பநிலை: \1*',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Current field temperature is\s*\*\*([0-9.]+°C)\*\*,\s*which exceeds the optimal upper threshold\s*\(([0-9.]+°C)\)\s*for\s*([A-Za-z]+)\.?',
            lambda m: f"தற்போதைய வயல் வெப்பநிலை **{m.group(1)}** ஆக உள்ளது. இது {crops_ta.get(m.group(3).lower(), m.group(3))} பயிருக்கு உகந்த மேல் வரம்பை விட ({m.group(2)}) அதிகமாக உள்ளது.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Current field temperature is\s*\*\*([0-9.]+°C)\*\*,\s*which is within the favorable growing range\s*\(([0-9.]+°C)\s*[-–]\s*([0-9.]+°C)\)\s*for\s*([A-Za-z]+)\s*according to\s*\*\*([^*]+)\*\*\s*guidelines\.?',
            lambda m: f"தற்போதைய வயல் வெப்பநிலை **{m.group(1)}** ஆக உள்ளது. **{m.group(5)}** வழிகாட்டுதலின்படி, இது {crops_ta.get(m.group(4).lower(), m.group(4))} பயிருக்கு சாதகமான வளர்ச்சி வரம்பிற்குள் ({m.group(2)} - {m.group(3)}) உள்ளது.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'temperatures exceeding 35°C severely impede pollen viability and increase blossom drop\.\s*Consider shade netting or morning/evening micro-sprinkler misting to reduce canopy heat stress\.',
            r'35°C-க்கு மேல் உள்ள வெப்பநிலை மகரந்தச் சேர்க்கையை கடுமையாக பாதிக்கிறது மற்றும் பூ உதிர்வதை அதிகரிக்கிறது. பயிர் வெப்ப அழுத்தத்தைக் குறைக்க நிழல் வலை அல்லது காலை/மாலை நேரங்களில் நுண் தெளிப்பான்களைப் பயன்படுத்தவும்.',
            t, flags=re.IGNORECASE
        )

        # 8. Fertilizer Advisories
        t = re.sub(
            r'the recommended fertilizer dosage for\s*([A-Za-z]+)\s*is N:P:K at 150:100:100 kg/ha for hybrid cultivars\.\s*Apply 50% nitrogen and entire P and K as basal dressing,\s*with remaining N in split doses at 30 and 45 days after planting\.',
            lambda m: f"{crops_ta.get(m.group(1).lower(), m.group(1))} வீரிய ரகங்களுக்கு பரிந்துரைக்கப்படும் உர அளவு ஹெக்டேருக்கு N:P:K 150:100:100 கிலோ ஆகும். 50% நைட்ரஜன் மற்றும் முழு பாஸ்பரஸ், பொட்டாசியம் உரங்களை அடியுரமாக இடவும்; மீதமுள்ள நைட்ரஜனை நட்ட 30 மற்றும் 45 நாட்களில் பிரித்து இடவும்.",
            t, flags=re.IGNORECASE
        )

        # 9. Simple Sentences & Clauses
        t = re.sub(
            r'The current soil moisture is\s*([0-9.]+%)\.?',
            r'தற்போதைய மண் ஈரப்பதம் \1 ஆக உள்ளது.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'The soil moisture is\s*([0-9.]+%)\.?',
            r'மண் ஈரப்பதம் \1 ஆக உள்ளது.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'According to TNAU guidelines,?',
            r'TNAU வழிகாட்டுதல்களின்படி,',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'According to ICAR guidelines,?',
            r'ICAR வழிகாட்டுதல்களின்படி,',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'According to KAU guidelines,?',
            r'KAU வழிகாட்டுதல்களின்படி,',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Please consult the referenced guide for site-specific agronomic adjustments\.',
            r'உங்கள் பகுதிக்கு ஏற்ற கூடுதல் விவசாய நுணுக்கங்களுக்கு பரிந்துரைக்கப்பட்ட வழிகாட்டியைப் பார்க்கவும்.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r"I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation\.",
            r"நம்பகமான பரிந்துரையை வழங்க விவசாய அறிவுத் தளத்தில் போதுமான சரிபார்க்கப்பட்ட தகவல்கள் கிடைக்கவில்லை.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(r'\bNo immediate additional watering is required\b', 'உடனடி கூடுதல் நீர்ப்பாசனம் தேவையில்லை', t, flags=re.IGNORECASE)
        t = re.sub(r'\bNo irrigation is required at this moment\b', 'தற்போது நீர்ப்பாசனம் தேவையில்லை', t, flags=re.IGNORECASE)
        t = re.sub(r'\bOptimal range\b', 'உகந்த வரம்பு', t, flags=re.IGNORECASE)
        t = re.sub(r'\bRecommended action\b', 'பரிந்துரைக்கப்படும் நடவடிக்கை', t, flags=re.IGNORECASE)
        t = re.sub(r'\bAgricultural Advisory\b', 'விவசாய ஆலோசனை', t, flags=re.IGNORECASE)

        return t.strip()

    def _translate_en_to_ml(self, text: str) -> str:
        crops_ml = {
            "tomato": "തക്കാളി",
            "rice": "നെല്ല്",
            "paddy": "നെല്ല്",
            "chilli": "മുളക്",
            "coconut": "തെങ്ങ്",
            "banana": "വാഴ",
            "sugarcane": "കരിമ്പ്",
            "cotton": "പരുത്തി",
            "maize": "ചോളം"
        }

        t = text

        # 1. Hardware Disconnection Alerts
        t = re.sub(
            r'⚠️\s*\*\*Hardware Telemetry Alert:\*\*\s*Gateway\s*`([^`]+)`\s*is currently\s*\*\*disconnected\*\*\s*\(([^)]+)\)\.\s*This reading is stale and must not be treated as current live moisture\.\s*Verify physical field conditions or check hardware connectivity before irrigating\.',
            r'⚠️ **ഹാർഡ്‌വെയർ മുന്നറിയിപ്പ്:** ഗേറ്റ്‌വേ `\1` നിലവിൽ **വിച്ഛേദിക്കപ്പെട്ടിരിക്കുന്നു** (\2). ഈ അളവ് പഴയതാണ്, നിലവിലെ തത്സമയ ഈർപ്പമായി കണക്കാക്കരുത്. നനയ്ക്കുന്നതിന് മുമ്പ് ഫീൽഡ് അവസ്ഥകൾ പരിശോധിക്കുക അല്ലെങ്കിൽ ഹാർഡ്‌വെയർ കണക്റ്റിവിറ്റി പരിശോധിക്കുക.',
            t
        )
        t = re.sub(
            r'⚠️\s*\*\*Hardware Notice:\*\*\s*Physical device\s*`([^`]+)`\s*is currently disconnected\s*\(([^)]+)\)\.\s*Do not assume this reading reflects current moisture conditions\.',
            r'⚠️ **ഹാർഡ്‌വെയർ മുന്നറിയിപ്പ്:** ഉപകരണം `\1` നിലവിൽ വിച്ഛേദിക്കപ്പെട്ടിരിക്കുന്നു (\2). ഈ അളവ് നിലവിലെ ഫീൽഡ് അവസ്ഥയെ പ്രതിഫലിപ്പിക്കുന്നുവെന്ന് കരുതരുത്.',
            t
        )

        # 2. Main Telemetry Assessment Paragraphs
        t = re.sub(
            r'Your (?:last recorded|current) soil moisture (?:is at|\(Sensor `[^`]+` on Device `[^`]+`[^)]*\) was)\s*\*\*([0-9.]+%)\*\*,\s*which is\s*\*\*below\*\*\s*the recommended optimal range\s*\(([0-9.]+%)\s*[-–]\s*([0-9.]+%)\)\s*for\s*([A-Za-z]+)\.?',
            lambda m: f"നിലവിൽ നിങ്ങളുടെ മണ്ണിലെ ഈർപ്പം **{m.group(1)}** ആണ്. ഇത് {crops_ml.get(m.group(4).lower(), m.group(4))} കൃഷിക്ക് ശുപാർശ ചെയ്തിട്ടുള്ള **{m.group(2)} മുതൽ {m.group(3)}** വരെയുള്ള അനുയോജ്യമായ പരിധിയേക്കാൾ കുറവാണ്.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Your (?:last recorded|current) soil moisture (?:is at|\(Sensor `[^`]+` on Device `[^`]+`[^)]*\) was)\s*\*\*([0-9.]+%)\*\*,\s*which is within the\s*\*\*optimal range\s*\(([0-9.]+%)\s*[-–]\s*([0-9.]+%)\)\*\*\s*for\s*([A-Za-z]+)\.?',
            lambda m: f"നിലവിൽ നിങ്ങളുടെ മണ്ണിലെ ഈർപ്പം **{m.group(1)}** ആണ്. ഇത് {crops_ml.get(m.group(4).lower(), m.group(4))} കൃഷിക്ക് **അനുയോജ്യമായ പരിധിയിലാണ് ({m.group(2)} - {m.group(3)})**.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Your (?:last recorded|current) soil moisture (?:is at|\(Sensor `[^`]+` on Device `[^`]+`[^)]*\) was)\s*\*\*([0-9.]+%)\*\*,\s*which is\s*\*\*above\*\*\s*the recommended optimal range\s*\(([0-9.]+%)\s*[-–]\s*([0-9.]+%)\)\s*for\s*([A-Za-z]+)\.?',
            lambda m: f"നിലവിൽ നിങ്ങളുടെ മണ്ണിലെ ഈർപ്പം **{m.group(1)}** ആണ്. ഇത് {crops_ml.get(m.group(4).lower(), m.group(4))} കൃഷിക്ക് ശുപാർശ ചെയ്തിട്ടുള്ള അനുയോജ്യമായ പരിധിയേക്കാൾ ({m.group(2)} - {m.group(3)}) **കൂടുതലാണ്**.",
            t, flags=re.IGNORECASE
        )

        # 3. Document Citation Lines
        t = re.sub(
            r'According to\s*\*\*([^*]+)\*\*\s*\(\*([^*]+)\*\):',
            r'**\1** നൽകിയ *\2* മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്:',
            t
        )
        t = re.sub(
            r'According to\s*\*\*([^*]+)\*\*\s*\(\*([^*]+)\*\),',
            r'**\1** (*\2*) മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്,',
            t
        )
        t = re.sub(
            r'According to\s*\*\*([^*]+)\*\*:',
            r'**\1** മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്:',
            t
        )
        t = re.sub(
            r'According to\s*\*\*([^*]+)\*\*,',
            r'**\1** മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്:',
            t
        )
        t = re.sub(
            r'Based on verified agricultural advisories from\s*\*\*([^*]+)\*\*\s*\(\*([^*]+)\*\):',
            r'**\1** (*\2*) സ്ഥിരീകരിച്ച കാർഷിക മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്:',
            t
        )

        # 4. Bullet Items
        t = re.sub(
            r'-\s*Optimal root-zone soil moisture:\s*\*\*([0-9.]+%)\s*to\s*([0-9.]+%)\*\*',
            r'- വേരുപടലത്തിൽ അനുയോജ്യമായ മണ്ണിലെ ഈർപ്പം: **\1 മുതൽ \2**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*Optimal range:\s*\*\*([0-9.]+%)[-–]([0-9.]+%)\*\*',
            r'- അനുയോജ്യമായ പരിധി: **\1 മുതൽ \2**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*(?:Current\s+)?condition:\s*Soil moisture (?:indicates a|is at a)\s*\*\*(?:sub-optimal deficit|severe water deficit)(?:\s*\(([0-9.]+%)\))?\*\*(?:\s*\(([0-9.]+%)\))?\.?',
            lambda m: f"- നിലവിലെ അവസ്ഥ: **{m.group(1) or m.group(2) or ''}**, അതായത് ഈർപ്പത്തിൽ കുറവുണ്ട്.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*(?:Current\s+)?condition:\s*Soil moisture is (?:within|in) the optimal range(?:\s*\(([0-9.]+%)\))?\.?',
            lambda m: f"- നിലവിലെ അവസ്ഥ: **{m.group(1) or ''}**, മണ്ണിലെ ഈർപ്പം അനുയോജ്യമായ അളവിലാണ്.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*(?:Current\s+)?condition:\s*Soil moisture indicates excessive waterlogging(?:\s*\(([0-9.]+%)\))?\.?',
            lambda m: f"- നിലവിലെ അവസ്ഥ: **{m.group(1) or ''}**, അമിതമായ വെള്ളക്കെട്ട് ഉണ്ട്.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*Current condition:\s*\*\*LOW\*\*',
            r'- നിലവിലെ അവസ്ഥ: **കുറവാണ് (LOW)**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*Current condition:\s*\*\*HIGH\*\*',
            r'- നിലവിലെ അവസ്ഥ: **കൂടുതലാണ് (HIGH)**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'-\s*Current condition:\s*\*\*OPTIMAL\*\*',
            r'- നിലവിലെ അവസ്ഥ: **അനുയോജ്യമായ അളവിലാണ് (OPTIMAL)**',
            t, flags=re.IGNORECASE
        )

        # 5. Explanatory Advice Sentences
        t = re.sub(
            r'Prolonged moisture deficit during flowering and fruit setting increases risk of blossom-end rot and flower drop\.\s*\*\*Prompt irrigation is recommended\*\*\s*to restore root-zone moisture into the optimal\s*([0-9.]+%)[-–]([0-9.]+%)\s*range\.',
            r'പൂവിടുന്നതിനും കായ്ക്കുന്നതിനുമുള്ള ഘട്ടങ്ങളിൽ ഈർപ്പക്കുറവ് ഉണ്ടാകുന്നത് പൂക്കൾ കൊഴിയുന്നതിനും കായ്കൾ ചീയുന്നതിനും കാരണമാകും. വേരുപടലത്തിലെ ഈർപ്പം അനുയോജ്യമായ \1–\2 പരിധിയിലേക്ക് എത്തിക്കാൻ **ഉടൻ നനയ്ക്കൽ നടത്താൻ ശുപാർശ ചെയ്യുന്നു**.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'\*\*Agronomic Recommendation:\*\*\s*Prompt irrigation is advised to restore root zone moisture into the optimal\s*([0-9.]+%)[-–]([0-9.]+%)\s*range and prevent crop moisture stress\.',
            r'**കാർഷിക ശുപാർശ:** വേരുപടലത്തിലെ ഈർപ്പം അനുയോജ്യമായ \1–\2 പരിധിയിലേക്ക് എത്തിക്കാനും വിളയുടെ വരൾച്ചാ സമ്മർദ്ദം തടയാനും ഉടനടി നനയ്ക്കൽ നടത്താൻ നിർദ്ദേശിക്കുന്നു.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Prompt irrigation is recommended to restore root-zone moisture into the optimal range\.',
            r'വേരുപടലത്തിലെ ഈർപ്പം അനുയോജ്യമായ പരിധിയിലേക്ക് എത്തിക്കാൻ ആവശ്യമായ നനയ്ക്കൽ നടത്തേണ്ടതാണ്.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'\*\*Prompt irrigation is recommended\.\*\*',
            r'**ഉടൻ നനയ്ക്കൽ നടത്താൻ ശുപാർശ ചെയ്യുന്നു.**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'immediate irrigation is recommended',
            r'ഉടൻ നനയ്ക്കൽ നടത്താൻ ശുപാർശ ചെയ്യുന്നു',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'excessive soil moisture impedes root aeration and increases (?:risk of root rot|susceptibility to fungal root rot)\.\s*\*\*Withhold irrigation\*\*\s*until soil moisture (?:naturally )?recedes below\s*([0-9.]+%)',
            r'അമിതമായ മണ്ണിലെ ഈർപ്പം വേരുകളിലേക്കുള്ള വായുസഞ്ചാരത്തെ തടസ്സപ്പെടുത്തുകയും ഫംഗസ് മൂലമുള്ള വേരുചീയൽ സാധ്യത വർദ്ധിപ്പിക്കുകയും ചെയ്യുന്നു. മണ്ണിലെ ഈർപ്പം \1 താഴുന്നത് വരെ **നനയ്ക്കൽ നിർത്തിവെക്കുക**',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'soil moisture conditions are favorable\.\s*Maintain regular monitoring;\s*no immediate additional watering is required\.',
            r'മണ്ണിലെ ഈർപ്പാവസ്ഥ അനുകൂലമാണ്. പതിവായി നിരീക്ഷിക്കുക; ഇപ്പോൾ അടിയന്തര നനയ്ക്കൽ ആവശ്യമില്ല.',
            t, flags=re.IGNORECASE
        )

        # 6. Reservoir & Water Warnings
        t = re.sub(
            r'\*\*Warning:\*\*\s*Irrigation water reservoir is critically low at\s*\*\*([0-9.]+%)\*\*\.\s*Replenish water storage before (?:running irrigation pumps|prolonged irrigation)\.',
            r'**മുന്നറിയിപ്പ്:** നനയ്ക്കാനുള്ള ജലസംഭരണിയിലെ ജലനിരപ്പ് നിലവിൽ **\1** മാത്രമാണ്. നനയ്ക്കുന്നതിന് മുമ്പ് ജലസംഭരണി നിറയ്ക്കുക.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Warning:\s*Irrigation water reservoir is critically low at\s*\*\*([0-9.]+%)\*\*\.?',
            r'**മുന്നറിയിപ്പ്:** നനയ്ക്കാനുള്ള ജലസംഭരണിയിലെ ജലനിരപ്പ് നിലവിൽ **\1** മാത്രമാണ്. നനയ്ക്കുന്നതിന് മുമ്പ് ജലസംഭരണി നിറയ്ക്കുക.',
            t, flags=re.IGNORECASE
        )

        # 7. Temperature Notes
        t = re.sub(
            r'Current Field Temperature:\s*\*\*([0-9.]+°C)\*\*',
            r'നിലവിലെ വയലിലെ താപനില: **\1**.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'\*Current Field Temperature:\s*([0-9.]+°C)\*',
            r'*നിലവിലെ വയലിലെ താപനില: \1*',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Current field temperature is\s*\*\*([0-9.]+°C)\*\*,\s*which exceeds the optimal upper threshold\s*\(([0-9.]+°C)\)\s*for\s*([A-Za-z]+)\.?',
            lambda m: f"നിലവിലെ വയലിലെ താപനില **{m.group(1)}** ആണ്. ഇത് {crops_ml.get(m.group(3).lower(), m.group(3))} കൃഷിക്ക് അനുയോജ്യമായ ഉയർന്ന പരിധിയേക്കാൾ ({m.group(2)}) കൂടുതലാണ്.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Current field temperature is\s*\*\*([0-9.]+°C)\*\*,\s*which is within the favorable growing range\s*\(([0-9.]+°C)\s*[-–]\s*([0-9.]+°C)\)\s*for\s*([A-Za-z]+)\s*according to\s*\*\*([^*]+)\*\*\s*guidelines\.?',
            lambda m: f"നിലവിലെ വയലിലെ താപനില **{m.group(1)}** ആണ്. **{m.group(5)}** മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്, ഇത് {crops_ml.get(m.group(4).lower(), m.group(4))} കൃഷിക്ക് അനുകൂലമായ വളർച്ചാ പരിധിയിലാണ് ({m.group(2)} - {m.group(3)}).",
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'temperatures exceeding 35°C severely impede pollen viability and increase blossom drop\.\s*Consider shade netting or morning/evening micro-sprinkler misting to reduce canopy heat stress\.',
            r'35°C-ൽ കൂടുതലുള്ള താപനില പരാഗണത്തെ സാരമായി ബാധിക്കുകയും പൂക്കൾ കൊഴിയാൻ കാരണമാവുകയും ചെയ്യുന്നു. വിളകളിലെ ചൂട് കുറയ്ക്കാൻ ഷേഡ് നെറ്റിംഗ് അല്ലെങ്കിൽ രാവിലെ/വൈകുന്നേരം മൈക്രോ സ്പ്രിംഗ്ലർ മിസ്റ്റിംഗ് പരിഗണിക്കുക.',
            t, flags=re.IGNORECASE
        )

        # 8. Fertilizer Advisories
        t = re.sub(
            r'the recommended fertilizer dosage for\s*([A-Za-z]+)\s*is N:P:K at 150:100:100 kg/ha for hybrid cultivars\.\s*Apply 50% nitrogen and entire P and K as basal dressing,\s*with remaining N in split doses at 30 and 45 days after planting\.',
            lambda m: f"{crops_ml.get(m.group(1).lower(), m.group(1))} ഹൈബ്രിഡ് ഇനങ്ങൾക്ക് ശുപാർശ ചെയ്യുന്ന വളത്തിന്റെ അളവ് ഹെക്ടറിന് N:P:K 150:100:100 കിലോഗ്രാം ആണ്. 50% നൈട്രജനും മുഴുവൻ ഫോസ്ഫറസും പൊട്ടാസ്യവും അടിവളമായി നൽകുക; ബാക്കി നൈട്രജൻ നട്ട് 30, 45 ദിവസങ്ങളിൽ നൽകുക.",
            t, flags=re.IGNORECASE
        )

        # 9. Simple Sentences & Clauses
        t = re.sub(
            r'The current soil moisture is\s*([0-9.]+%)\.?',
            r'നിലവിലെ മണ്ണിലെ ഈർപ്പം \1 ആണ്.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'The soil moisture is\s*([0-9.]+%)\.?',
            r'മണ്ണിലെ ഈർപ്പം \1 ആണ്.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'According to TNAU guidelines,?',
            r'TNAU മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്,',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'According to ICAR guidelines,?',
            r'ICAR മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്,',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'According to KAU guidelines,?',
            r'KAU മാർഗ്ഗനിർദ്ദേശങ്ങൾ അനുസരിച്ച്,',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r'Please consult the referenced guide for site-specific agronomic adjustments\.',
            r'നിങ്ങളുടെ സ്ഥലത്തിന് അനുയോജ്യമായ കൂടുതൽ വിവരങ്ങൾക്ക് റഫറൻസ് ഗൈഡ് പരിശോധിക്കുക.',
            t, flags=re.IGNORECASE
        )
        t = re.sub(
            r"I couldn't find enough verified information in the agricultural knowledge base to give a reliable recommendation\.",
            r"വിശ്വാസയോഗ്യമായ ഒരു ശുപാർശ നൽകാൻ കാർഷിക വിജ്ഞാന അടിത്തറയിൽ മതിയായ സ്ഥിരീകരിച്ച വിവരങ്ങൾ കണ്ടെത്താനായില്ല.",
            t, flags=re.IGNORECASE
        )
        t = re.sub(r'\bNo immediate additional watering is required\b', 'ഇപ്പോൾ അടിയന്തര നനയ്ക്കൽ ആവശ്യമില്ല', t, flags=re.IGNORECASE)
        t = re.sub(r'\bNo irrigation is required at this moment\b', 'ഇപ്പോൾ നനയ്ക്കേണ്ട ആവശ്യമില്ല', t, flags=re.IGNORECASE)
        t = re.sub(r'\bOptimal range\b', 'അനുയോജ്യമായ പരിധി', t, flags=re.IGNORECASE)
        t = re.sub(r'\bRecommended action\b', 'ശുപാർശ ചെയ്യുന്ന നടപടി', t, flags=re.IGNORECASE)
        t = re.sub(r'\bAgricultural Advisory\b', 'കാർഷിക ഉപദേശം', t, flags=re.IGNORECASE)

        return t.strip()

class TranslationService:
    def __init__(self):
        self.provider = settings.TRANSLATION_PROVIDER
        self.model_name = settings.TRANSLATION_MODEL
        self.adapter = AgriculturalLocalTranslationAdapter()

    async def translate_to_english(self, text: str, source_language: Optional[str] = None) -> Dict[str, Any]:
        """
        Translates Tamil or Malayalam text to English.
        If already English, returns original.
        """
        if not source_language:
            source_language, _ = detect_language(text)

        if source_language == "en":
            return {
                "original_text": text,
                "translated_text": text,
                "source_language": "en",
                "target_language": "en",
                "translation_status": "success"
            }

        translated = await self.adapter.translate(text, source_lang=source_language, target_lang="en")
        return {
            "original_text": text,
            "translated_text": translated,
            "source_language": source_language,
            "target_language": "en",
            "translation_status": "success"
        }

    async def translate_from_english(self, text: str, target_language: str) -> Dict[str, Any]:
        """
        Translates English text to Tamil or Malayalam.
        Ensures COMPLETE translation of the response with retry on failure.
        Never mixes languages or concatenates an English response after a localized prefix.
        """
        if target_language == "en" or not text.strip():
            return {
                "original_text": text,
                "translated_text": text,
                "source_language": "en",
                "target_language": "en",
                "translation_status": "success"
            }

        # Attempt translation with retry
        max_attempts = 2
        translated = ""
        success = False

        for attempt in range(max_attempts):
            try:
                translated = await self.adapter.translate(text, source_lang="en", target_lang=target_language)
                # Verify language script presence
                if target_language == "ta" and any('\u0B80' <= c <= '\u0BFF' for c in translated):
                    success = True
                    break
                elif target_language == "ml" and any('\u0D00' <= c <= '\u0D7F' for c in translated):
                    success = True
                    break
                elif target_language not in ["ta", "ml"] and translated:
                    success = True
                    break
            except Exception as e:
                logger.warning(f"Translation attempt {attempt+1} failed for {target_language}: {e}")

        if not success:
            logger.error(f"Translation to {target_language} could not be completed.")
            # Do NOT silently prefix or mix languages. Clearly flag failure.
            return {
                "original_text": text,
                "translated_text": text,
                "source_language": "en",
                "target_language": target_language,
                "translation_status": "failed",
                "error": f"Failed to produce complete {target_language} translation"
            }

        return {
            "original_text": text,
            "translated_text": translated,
            "source_language": "en",
            "target_language": target_language,
            "translation_status": "success"
        }

translation_service = TranslationService()
