import os
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.config.settings import settings
from app.database.session import get_db
from app.models.document import Document
from app.schemas.rag import (
    DocumentResponse,
    KnowledgeSearchRequest,
    RAGDebugInfo,
    RAGQueryRequest,
    RAGQueryResponse,
    SourceCitation,
)
from app.services.rag_service import rag_service
from app.services.context_service import context_service
from app.services.ai_service import ai_service
from app.services.translation_service import translation_service
from app.utils.lang_detect import detect_language

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base & RAG Management"])

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all indexed agricultural documents with full metadata."""
    res = await db.execute(select(Document).order_by(desc(Document.created_at)))
    docs = res.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]

@router.post("/upload", response_model=DocumentResponse)
async def upload_and_ingest_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    crop: Optional[str] = Form("Tomato"),
    crop_type: Optional[str] = Form("Horticulture"),
    organization: Optional[str] = Form("TNAU - Tamil Nadu Agricultural University"),
    source: Optional[str] = Form("Agricultural University Cultivation Advisory"),
    author: Optional[str] = Form("Agronomy Department"),
    region: Optional[str] = Form("South India"),
    state: Optional[str] = Form("Tamil Nadu"),
    soil_type: Optional[str] = Form("Red Loam / Clay"),
    topic: Optional[str] = Form("Irrigation, Soil and Crop Management"),
    language: Optional[str] = Form("English"),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests agricultural PDF/DOCX/TXT file:
    Extracts text -> Chunks -> Embeds -> Writes to ChromaDB & PostgreSQL.
    """
    filename = file.filename or f"doc_{uuid.uuid4().hex[:8]}.txt"
    ext = filename.lower().split('.')[-1]
    if ext not in ["pdf", "docx", "doc", "txt", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Supported formats: PDF, DOCX, TXT, MD"
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    save_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{filename}")

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    meta = {
        "document_id": doc_id,
        "title": title or filename.rsplit('.', 1)[0].replace("_", " ").title(),
        "crop": crop,
        "crop_type": crop_type,
        "organization": organization,
        "source": source,
        "author": author,
        "region": region,
        "state": state,
        "soil_type": soil_type,
        "topic": topic,
        "language": language,
    }

    try:
        ingest_res = rag_service.ingest_document(save_path, meta)
        chunk_count = ingest_res.get("chunk_count", 0)

        # Store in database
        doc_record = Document(
            id=doc_id,
            title=meta["title"],
            source=source,
            organization=organization,
            author=author,
            crop=crop,
            crop_type=crop_type,
            state=state,
            region=region,
            soil_type=soil_type,
            topic=topic,
            language=language,
            document_type=ext.upper(),
            file_path=save_path,
            file_size=file_size,
            chunk_count=chunk_count,
            status="indexed"
        )
        db.add(doc_record)
        await db.commit()
        await db.refresh(doc_record)

        return DocumentResponse.model_validate(doc_record)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}"
        )

@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes document from ChromaDB vector store and PostgreSQL registry."""
    res = await db.execute(select(Document).where(Document.id == document_id))
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    rag_service.delete_document(document_id)
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass

    await db.delete(doc)
    await db.commit()
    return None

@router.post("/search")
async def search_knowledge(req: KnowledgeSearchRequest):
    """Admin semantic search interface across indexed agricultural chunks."""
    chunks = rag_service.retrieve(
        query=req.query,
        crop=req.crop,
        region=req.region,
        topic=req.topic,
        top_k=req.top_k
    )
    return {
        "query": req.query,
        "count": len(chunks),
        "results": chunks
    }

@router.post("/rag-debug", response_model=RAGDebugInfo)
async def debug_rag_pipeline(
    req: RAGQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Developer/Admin RAG Diagnostic Panel.
    Inspects user query translation, retrieved chunks, similarity scores,
    synthesized sensor context, final prompt, and raw model output.
    """
    detected_lang, _ = detect_language(req.question)
    trans = await translation_service.translate_to_english(req.question, source_language=detected_lang)
    english_query = trans["translated_text"]

    ctx = await context_service.build_context(
        question=english_query,
        device_id=req.device_id,
        crop=req.crop,
        region=req.region,
        top_k=req.top_k or 5,
        db=db
    )

    reasoning = await ai_service.reason(
        question=english_query,
        rag_context=ctx["rag_context_text"],
        sensor_data=ctx["sensor_context"],
        sources=ctx["sources"],
        farm_info=ctx["farm_info"],
        crop=ctx["crop"]
    )

    return RAGDebugInfo(
        original_query=req.question,
        detected_language=detected_lang,
        translated_query=english_query,
        retrieved_chunks=ctx["retrieved_chunks"],
        sensor_context=ctx["sensor_context"],
        final_prompt=reasoning["prompt"],
        llm_raw_response=reasoning["answer"],
        sources=ctx["sources"]
    )
