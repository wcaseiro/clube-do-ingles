from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import InviteLink

router = APIRouter(prefix="/invites", tags=["invites"])

@router.get("/{code}")
def get_invite(code: str, db: Session = Depends(get_db)):
    invite = db.query(InviteLink).filter(func.lower(InviteLink.code) == code.lower()).first()
    if not invite or not invite.class_:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    return {
        "code": invite.code,
        "class_name": invite.class_.name,
        "level": invite.class_.level,
        "is_active": invite.is_active and invite.class_.is_active,
        "used_count": invite.used_count,
        "max_uses": invite.max_uses,
    }
