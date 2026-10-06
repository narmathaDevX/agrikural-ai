import os
import uuid
import logging
from typing import Optional, Dict, Any
from app.config.settings import settings

logger = logging.getLogger("agrikural.tts")

class BaseTTSAdapter:
    async def synthesize(self, text: str, language: str) -> Optional[str]:
        """Synthesizes speech to an audio file and returns the file path."""
        raise NotImplementedError

class GTTSSpeechAdapter(BaseTTSAdapter):
    """
    Adapter using Google Text-to-Speech (gTTS) library for high-quality Tamil, Malayalam, and English.
    Requires no paid API keys.
    """
    async def synthesize(self, text: str, language: str) -> Optional[str]:
        try:
            from gtts import gTTS
            clean_text = text.strip()
            if not clean_text:
                return None

            # Truncate to reasonable TTS length (first 400 chars) for fast real-time audio response
            if len(clean_text) > 400:
                clean_text = clean_text[:400] + "..."

            lang_code = language.lower()
            if lang_code not in ["ta", "ml", "en"]:
                lang_code = "en"

            file_id = f"speech_{uuid.uuid4().hex[:12]}.mp3"
            target_path = os.path.join(settings.AUDIO_DIR, file_id)

            tts = gTTS(text=clean_text, lang=lang_code, slow=False)
            tts.save(target_path)
            logger.info(f"Generated TTS audio ({lang_code}): {target_path}")
            return file_id
        except Exception as e:
            logger.error(f"gTTS synthesis failed: {e}. Falling back to empty audio.")
            return None

class LocalFallbackTTSAdapter(BaseTTSAdapter):
    async def synthesize(self, text: str, language: str) -> Optional[str]:
        # Generates a minimal placeholder or silent mp3 header if offline
        file_id = f"speech_fallback_{uuid.uuid4().hex[:8]}.mp3"
        target_path = os.path.join(settings.AUDIO_DIR, file_id)
        # Create minimal 1-second silent MP3 buffer
        with open(target_path, "wb") as f:
            f.write(b'\xff\xfb\x90\x00\x00\x00\x00\x00' * 10)
        return file_id

class TTSService:
    def __init__(self):
        self.provider = settings.TTS_PROVIDER.lower()
        if self.provider == "gtts":
            self.adapter = GTTSSpeechAdapter()
        else:
            self.adapter = LocalFallbackTTSAdapter()

    async def generate_speech(self, text: str, language: str) -> Dict[str, Any]:
        """
        Generate spoken audio for text in Tamil, Malayalam, or English.
        Returns:
            {
                "audio_url": "/api/voice/audio/<id>.mp3",
                "language": language,
                "format": "mp3"
            }
        """
        file_id = await self.adapter.synthesize(text, language)
        if not file_id:
            # Try fallback adapter
            file_id = await LocalFallbackTTSAdapter().synthesize(text, language)

        audio_url = f"/api/voice/audio/{file_id}" if file_id else None
        return {
            "audio_url": audio_url,
            "language": language,
            "format": "mp3"
        }

tts_service = TTSService()
