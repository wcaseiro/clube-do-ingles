from datetime import datetime, timedelta
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from .models import ClassStudent, User, XPEvent, AIConversation, StudentProgress
from .avatar_rewards import avatar_stage_for_xp

TRAIL_EVENTS = ["lesson_completed", "quiz_completed", "quiz_bonus", "module_challenge"]
CONVERSATION_EVENTS = ["ai_chat"]

def _class_user_ids(db: Session, class_id: int):
    return [row.user_id for row in db.query(ClassStudent).filter(ClassStudent.class_id == class_id, ClassStudent.status == "active").all()]

def _row(position: int, user: User, xp: int, extra: dict | None = None):
    avatar_info = avatar_stage_for_xp(user.total_xp or 0)
    data = {
        "position": position,
        "nickname": user.nickname,
        "avatar": user.avatar or avatar_info["avatar"],
        "evolution_avatar": avatar_info["avatar"],
        "evolution_stage": avatar_info["stage"],
        "evolution_name": avatar_info["name"],
        "xp": int(xp or 0),
        "total_xp": int(user.total_xp or 0),
    }
    if extra:
        data.update(extra)
    return data

def weekly_ranking(db: Session, class_id: int):
    start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    user_ids = _class_user_ids(db, class_id)
    if not user_ids:
        return []
    rows = db.query(
        User,
        func.coalesce(func.sum(XPEvent.points), 0).label("xp")
    ).outerjoin(
        XPEvent, (XPEvent.user_id == User.id) & (XPEvent.created_at >= start)
    ).filter(
        User.id.in_(user_ids), User.is_active == True
    ).group_by(User.id).order_by(func.coalesce(func.sum(XPEvent.points), 0).desc()).all()
    return [_row(i + 1, u, xp) for i, (u, xp) in enumerate(rows)]

def general_ranking(db: Session, class_id: int):
    user_ids = _class_user_ids(db, class_id)
    if not user_ids:
        return []
    rows = db.query(User).filter(User.id.in_(user_ids), User.is_active == True).order_by(User.total_xp.desc()).all()
    return [_row(i + 1, u, u.total_xp or 0) for i, u in enumerate(rows)]

def trail_ranking(db: Session, class_id: int):
    user_ids = _class_user_ids(db, class_id)
    if not user_ids:
        return []
    rows = db.query(
        User,
        func.coalesce(func.sum(XPEvent.points), 0).label("xp"),
        func.count(func.distinct(StudentProgress.lesson_id)).label("lessons")
    ).outerjoin(
        XPEvent, (XPEvent.user_id == User.id) & (XPEvent.event_type.in_(TRAIL_EVENTS))
    ).outerjoin(
        StudentProgress, (StudentProgress.user_id == User.id) & (StudentProgress.status == "completed")
    ).filter(
        User.id.in_(user_ids), User.is_active == True
    ).group_by(User.id).order_by(func.coalesce(func.sum(XPEvent.points), 0).desc(), func.count(func.distinct(StudentProgress.lesson_id)).desc()).all()
    return [_row(i + 1, u, xp, {"lessons_completed": int(lessons or 0), "score_type": "trail"}) for i, (u, xp, lessons) in enumerate(rows)]

def conversation_ranking(db: Session, class_id: int):
    user_ids = _class_user_ids(db, class_id)
    if not user_ids:
        return []
    rows = db.query(
        User,
        func.count(AIConversation.id).label("messages"),
        func.coalesce(func.sum(XPEvent.points), 0).label("xp")
    ).outerjoin(
        AIConversation, AIConversation.user_id == User.id
    ).outerjoin(
        XPEvent, (XPEvent.user_id == User.id) & (XPEvent.event_type.in_(CONVERSATION_EVENTS))
    ).filter(
        User.id.in_(user_ids), User.is_active == True
    ).group_by(User.id).order_by(func.count(AIConversation.id).desc(), func.coalesce(func.sum(XPEvent.points), 0).desc()).all()
    out = []
    for i, (u, messages, xp) in enumerate(rows):
        score = int(messages or 0) * 10 + int(xp or 0)
        out.append(_row(i + 1, u, score, {"messages": int(messages or 0), "conversation_xp": int(xp or 0), "score_type": "conversation"}))
    return out
