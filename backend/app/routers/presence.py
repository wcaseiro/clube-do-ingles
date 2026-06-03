from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..auth import get_current_user

router = APIRouter(prefix="/presence", tags=["presence"])

@router.post("/heartbeat")
def heartbeat(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.last_seen_at = datetime.utcnow()
    db.add(user)
    db.commit()
    return {"ok": True, "last_seen_at": user.last_seen_at}
