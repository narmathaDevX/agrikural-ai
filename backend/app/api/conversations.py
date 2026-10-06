from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.models.conversation import Conversation, Message
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.auth.jwt import get_current_user_optional

router = APIRouter(prefix="/conversations", tags=["Conversations & History"])

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    user_id: Optional[str] = Query(None),
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
    )
    if user_id:
        query = query.where(Conversation.user_id == user_id)

    result = await db.execute(query)
    convs = result.scalars().all()
    return [ConversationResponse.model_validate(c) for c in convs]

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conv_in: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional)
):
    conv = Conversation(
        title=conv_in.title or "Agricultural Consultation",
        device_id=conv_in.device_id,
        user_id=user.id if user else None,
        language=conv_in.language or "ta"
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    # Re-fetch with messages
    res = await db.execute(
        select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conv.id)
    )
    return ConversationResponse.model_validate(res.scalar_one())

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation_id)
    )
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return ConversationResponse.model_validate(conv)

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()
    return None
