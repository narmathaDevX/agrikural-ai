from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database.session import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertResponse, AlertResolve

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    device_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db)
):
    query = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    if device_id:
        query = query.where(Alert.device_id == device_id)
    if severity:
        query = query.where(Alert.severity == severity)
    if is_resolved is not None:
        query = query.where(Alert.is_resolved == is_resolved)

    result = await db.execute(query)
    alerts = result.scalars().all()
    return [AlertResponse.model_validate(a) for a in alerts]

@router.put("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    resolve_data: AlertResolve,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    alert.is_resolved = resolve_data.is_resolved
    alert.resolved_at = datetime.now(timezone.utc) if resolve_data.is_resolved else None

    await db.commit()
    await db.refresh(alert)
    return AlertResponse.model_validate(alert)
