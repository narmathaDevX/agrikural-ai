import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config.settings import settings
from app.database.session import get_db
from app.models.conversation import Conversation, Message
from app.schemas.voice import (
    STTResponse,
    TranslationRequest,
    TranslationResponse,
    TTSRequest,
    TTSResponse,
)
from app.schemas.rag import RAGQueryResponse
from app.services.speech_service import speech_service
from app.services.translation_service import translation_service
from app.services.tts_service import tts_service
from app.services.context_service import context_service
from app.services.ai_service import ai_service
from app.utils.lang_detect import detect_language

router = APIRouter(prefix="/voice", tags=["Voice & Multilingual AI Pipeline"])

@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    audio_file: UploadFile = File(...),
    language_override: Optional[str] = Form(None)
):
    """
    Transcribes audio into text and detects language (Tamil, Malayalam, English).
    """
    audio_bytes = await audio_file.read()
    result = await speech_service.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio_file.filename,
        language_override=language_override
    )
    return STTResponse(
        text=result["text"],
        language=result["language"],
        confidence=result["confidence"]
    )

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(req: TranslationRequest):
    """Translates text between Tamil/Malayalam and English."""
    if req.target_language == "en":
        res = await translation_service.translate_to_english(req.text, req.source_language)
    else:
        res = await translation_service.translate_from_english(req.text, req.target_language)

    return TranslationResponse(
        original_text=res["original_text"],
        translated_text=res["translated_text"],
        source_language=res["source_language"],
        target_language=res["target_language"]
    )

@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(req: TTSRequest):
    """Synthesizes text into speech audio."""
    res = await tts_service.generate_speech(req.text, req.language)
    return TTSResponse(
        audio_url=res["audio_url"] or "",
        language=res["language"],
        format=res["format"]
    )

@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """Streams generated audio mp3 files."""
    file_path = os.path.join(settings.AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg")

@router.post("/chat", response_model=RAGQueryResponse)
async def full_voice_chat_pipeline(
    text: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    device_id: Optional[str] = Form(None),
    language_override: Optional[str] = Form(None),
    crop: Optional[str] = Form(None),
    conversation_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    COMPLETE MULTILINGUAL VOICE + SENSOR + RAG PIPELINE:
    1. Speech-to-Text (if audio submitted)
    2. Automatic Language Detection (Tamil, Malayalam, English)
    3. Translation to English
    4. Sensor Data Extraction for Target Device
    5. ChromaDB RAG Semantic Document Retrieval
    6. Grounded AI Reasoning & Hallucination Prevention
    7. Translation of Answer to User's Language
    8. Text-to-Speech Synthesis
    9. Persistent Logging in PostgreSQL
    """
    input_text = ""
    lang_code = language_override

    # Step 1: STT if audio supplied
    if audio_file:
        audio_bytes = await audio_file.read()
        stt_res = await speech_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio_file.filename,
            language_override=language_override
        )
        input_text = stt_res["text"]
        if not lang_code:
            lang_code = stt_res["language"]
    elif text:
        input_text = text.strip()

    if not input_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either text or an audio file must be provided"
        )

    # Step 2: Language Detection
    if not lang_code:
        detected_lang, _ = detect_language(input_text)
        lang_code = detected_lang

    # Step 3: Translate query to English
    trans_res = await translation_service.translate_to_english(input_text, source_language=lang_code)
    english_query = trans_res["translated_text"]

    # Step 4 & 5: Build Hybrid Context (RAG + Sensor Data + Farm Info)
    context_data = await context_service.build_context(
        question=english_query,
        device_id=device_id,
        crop=crop,
        db=db
    )

    # Step 6: Grounded AI Reasoning
    reasoning_res = await ai_service.reason(
        question=english_query,
        rag_context=context_data["rag_context_text"],
        sensor_data=context_data["sensor_context"],
        sources=context_data["sources"],
        farm_info=context_data["farm_info"],
        crop=context_data["crop"]
    )
    english_answer = reasoning_res["answer"]

    # Step 7: Translate Answer back to User's Language
    if lang_code in ["ta", "ml"]:
        ans_trans = await translation_service.translate_from_english(english_answer, target_language=lang_code)
        translated_answer = ans_trans["translated_text"]
    else:
        translated_answer = english_answer

    # Step 8: Generate Spoken Audio in User's Language
    speech_res = await tts_service.generate_speech(translated_answer, language=lang_code)
    audio_url = speech_res["audio_url"]

    # Step 9: Store in Conversation History
    conv = None
    if conversation_id:
        c_res = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conv = c_res.scalar_one_or_none()

    if not conv:
        conv = Conversation(
            title=input_text[:50] + "..." if len(input_text) > 50 else input_text,
            device_id=device_id,
            language=lang_code
        )
        db.add(conv)
        await db.flush()

    # User message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        original_text=input_text,
        detected_language=lang_code,
        translated_english_text=english_query
    )
    db.add(user_msg)

    # Assistant message
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        original_text=english_answer,
        detected_language=lang_code,
        translated_english_text=english_answer,
        translated_output_text=translated_answer,
        audio_url=audio_url,
        retrieved_documents_json=[s.model_dump() for s in context_data["sources"]],
        sensor_context_json=context_data["sensor_context"]
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return RAGQueryResponse(
        answer=translated_answer,
        translated_answer=translated_answer,
        original_question=input_text,
        detected_language=lang_code,
        translated_question=english_query,
        sources=context_data["sources"],
        sensor_context=context_data["sensor_context"],
        language=lang_code,
        confidence_score=0.96,
        audio_url=audio_url,
        conversation_id=conv.id,
        message_id=assistant_msg.id
    )
