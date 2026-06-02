from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from .models import ClassStudent, User, XPEvent

def _class_user_ids(db: Session, class_id: int):
    return [row.user_id for row in db.query(ClassStudent).filter(ClassStudent.class_id == class_id, ClassStudent.status == "active").all()]

def weekly_ranking(db: Session, class_id: int):
    start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    user_ids = _class_user_ids(db, class_id)
    if not user_ids:
        return []
    rows = db.query(
        User.id, User.nickname, User.avatar, func.coalesce(func.sum(XPEvent.points), 0).label("xp")
    ).outerjoin(XPEvent, (XPEvent.user_id == User.id) & (XPEvent.created_at >= start)).filter(
        User.id.in_(user_ids), User.is_active == True
    ).group_by(User.id).order_by(func.coalesce(func.sum(XPEvent.points), 0).desc()).all()
    return [{"position": i + 1, "nickname": r.nickname, "avatar": r.avatar, "xp": int(r.xp or 0)} for i, r in enumerate(rows)]

def general_ranking(db: Session, class_id: int):
    user_ids = _class_user_ids(db, class_id)
    if not user_ids:
        return []
    rows = db.query(User).filter(User.id.in_(user_ids), User.is_active == True).order_by(User.total_xp.desc()).all()
    return [{"position": i + 1, "nickname": u.nickname, "avatar": u.avatar, "xp": u.total_xp or 0} for i, u in enumerate(rows)]
