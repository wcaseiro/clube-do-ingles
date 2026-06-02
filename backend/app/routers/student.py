from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import User, Class, ClassStudent, Lesson, StudentProgress, XPEvent, AIConversation
from ..auth import get_current_user
from ..ranking import weekly_ranking, general_ranking

router = APIRouter(prefix="/student", tags=["student"])

def current_class(db: Session, user: User):
    link = db.query(ClassStudent).filter(ClassStudent.user_id == user.id, ClassStudent.status == "active").first()
    if not link:
        return None
    return db.get(Class, link.class_id)

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = current_class(db, user)
    completed = db.query(StudentProgress).filter(StudentProgress.user_id == user.id, StudentProgress.status == "completed").count()
    total_lessons = db.query(Lesson).count()
    ai_count = db.query(AIConversation).filter(AIConversation.user_id == user.id).count()
    next_lesson = db.query(Lesson).outerjoin(StudentProgress, (StudentProgress.lesson_id == Lesson.id) & (StudentProgress.user_id == user.id)).filter(
        (StudentProgress.status == None) | (StudentProgress.status != "completed")
    ).order_by(Lesson.module_id, Lesson.order_index).first()
    return {
        "student": {"first_name": user.first_name, "nickname": user.nickname, "avatar": user.avatar, "level": user.level, "total_xp": user.total_xp, "streak_days": user.streak_days},
        "class": {"name": c.name, "code": c.code, "level": c.level} if c else None,
        "progress": {"completed_lessons": completed, "total_lessons": total_lessons, "percent": round((completed / total_lessons * 100), 1) if total_lessons else 0, "ai_conversations": ai_count},
        "mission": {"lesson_id": next_lesson.id, "title": next_lesson.title, "phrase_en": next_lesson.phrase_en} if next_lesson else None,
    }

@router.get("/profile")
def profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = current_class(db, user)
    return {
        "first_name": user.first_name, "nickname": user.nickname, "avatar": user.avatar, "level": user.level,
        "total_xp": user.total_xp, "streak_days": user.streak_days, "last_login_at": user.last_login_at,
        "class": c.name if c else None,
        "lessons_completed": db.query(StudentProgress).filter(StudentProgress.user_id == user.id, StudentProgress.status == "completed").count(),
        "ai_conversations": db.query(AIConversation).filter(AIConversation.user_id == user.id).count(),
    }

@router.get("/trail")
def trail(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..models import Module
    modules = db.query(Module).order_by(Module.order_index).all()
    out = []
    for m in modules:
        lessons = []
        for lesson in m.lessons:
            progress = db.query(StudentProgress).filter(StudentProgress.user_id == user.id, StudentProgress.lesson_id == lesson.id).first()
            lessons.append({"id": lesson.id, "title": lesson.title, "status": progress.status if progress else "available", "phrase_en": lesson.phrase_en})
        out.append({"id": m.id, "title": m.title, "description": m.description, "level": m.level, "lessons": sorted(lessons, key=lambda x: x["id"])})
    return out

@router.get("/ranking")
def ranking(kind: str = "weekly", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = current_class(db, user)
    if not c:
        return []
    return weekly_ranking(db, c.id) if kind == "weekly" else general_ranking(db, c.id)
