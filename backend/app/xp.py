from datetime import datetime, date
from sqlalchemy import func
from sqlalchemy.orm import Session
from .models import User, XPEvent

XP_LOGIN_DAILY = 5
XP_LESSON_COMPLETED = 20
XP_QUIZ_COMPLETED = 30
XP_QUIZ_BONUS = 20
XP_AI_CHAT = 40
XP_MODULE_CHALLENGE = 100

def add_xp(db: Session, user: User, event_type: str, points: int, description: str = "") -> int:
    event = XPEvent(user_id=user.id, event_type=event_type, points=points, description=description)
    user.total_xp = (user.total_xp or 0) + points
    db.add(event)
    db.add(user)
    db.commit()
    db.refresh(user)
    return points

def add_daily_login_xp(db: Session, user: User) -> int:
    today = date.today()
    existing = db.query(XPEvent).filter(
        XPEvent.user_id == user.id,
        XPEvent.event_type == "daily_login",
        func.date(XPEvent.created_at) == today.isoformat(),
    ).first()
    if existing:
        return 0
    return add_xp(db, user, "daily_login", XP_LOGIN_DAILY, "Login diário")

def add_ai_xp_once_per_day(db: Session, user: User) -> int:
    today = date.today()
    existing = db.query(XPEvent).filter(
        XPEvent.user_id == user.id,
        XPEvent.event_type == "ai_chat",
        func.date(XPEvent.created_at) == today.isoformat(),
    ).first()
    if existing:
        return 0
    return add_xp(db, user, "ai_chat", XP_AI_CHAT, "Conversou com a IA professora")
