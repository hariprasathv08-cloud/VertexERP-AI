from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import AuditLog, User
from backend.schemas import AuditLogOut
from backend.security import get_current_user

router = APIRouter(prefix="/api/logs", tags=["Audit Logs"])

@router.get("", response_model=List[AuditLogOut])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns lists of system audit logs, sorted chronologically by newest first.
    Capped to the most recent 100 entries for console performance.
    """
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return logs
