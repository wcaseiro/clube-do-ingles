from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Module, Lesson, StudentProgress, Quiz
from ..auth import get_current_user
from ..xp import add_xp, XP_LESSON_COMPLETED

router = APIRouter(tags=["lessons"])

@router.get("/modules")
def modules(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [{"id": m.id, "title": m.title, "description": m.description, "level": m.level, "order_index": m.order_index} for m in db.query(Module).order_by(Module.order_index).all()]

@router.get("/modules/{module_id}/lessons")
def module_lessons(module_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lessons = db.query(Lesson).filter(Lesson.module_id == module_id).order_by(Lesson.order_index).all()
    return [{"id": l.id, "title": l.title, "objective": l.objective, "phrase_en": l.phrase_en, "phrase_pt": l.phrase_pt, "order_index": l.order_index} for l in lessons]

@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Aula não encontrada")

    progress = db.query(StudentProgress).filter(
        StudentProgress.user_id == user.id,
        StudentProgress.lesson_id == lesson.id,
    ).first()

    module_lessons = db.query(Lesson).filter(
        Lesson.module_id == lesson.module_id
    ).order_by(Lesson.order_index).all()
    ids = [item.id for item in module_lessons]
    current_index = ids.index(lesson.id) if lesson.id in ids else 0
    previous_id = ids[current_index - 1] if current_index > 0 else None
    next_id = ids[current_index + 1] if current_index + 1 < len(ids) else None
    module = db.get(Module, lesson.module_id)
    quiz = db.query(Quiz).filter(Quiz.lesson_id == lesson.id).first()

    score = progress.score if progress else 0
    status = progress.status if progress else "available"

    return {
        "id": lesson.id,
        "module_id": lesson.module_id,
        "module_title": module.title if module else "",
        "position": current_index + 1,
        "total_in_module": len(module_lessons),
        "previous_id": previous_id,
        "next_id": next_id,
        "title": lesson.title,
        "objective": lesson.objective,
        "phrase_en": lesson.phrase_en,
        "phrase_pt": lesson.phrase_pt,
        "example_en": lesson.example_en,
        "example_pt": lesson.example_pt,
        "status": status,
        "score": score,
        "quiz_required": bool(quiz),
        "quiz_passed": score >= 80,
    }

@router.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Aula não encontrada")

    quiz = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    progress = db.query(StudentProgress).filter(
        StudentProgress.user_id == user.id,
        StudentProgress.lesson_id == lesson_id,
    ).first()

    if quiz and (not progress or (progress.score or 0) < 80):
        raise HTTPException(
            status_code=400,
            detail="Antes de concluir a aula, faça o quiz e acerte a resposta. O quiz é obrigatório para avançar.",
        )

    already = progress and progress.status == "completed"
    if not progress:
        progress = StudentProgress(user_id=user.id, lesson_id=lesson_id)

    progress.status = "completed"
    progress.score = max(progress.score or 0, 100)
    progress.completed_at = datetime.utcnow()
    db.add(progress)
    db.commit()

    points = 0 if already else add_xp(db, user, "lesson_completed", XP_LESSON_COMPLETED, f"Concluiu a aula {lesson.title}")
    return {
        "ok": True,
        "points": points,
        "message": "Aula concluída!" if points else "Essa aula já estava concluída.",
        "next_id": get_next_lesson_id(db, lesson),
    }

def get_next_lesson_id(db: Session, lesson: Lesson):
    next_lesson = db.query(Lesson).filter(
        Lesson.module_id == lesson.module_id,
        Lesson.order_index > lesson.order_index,
    ).order_by(Lesson.order_index).first()
    if next_lesson:
        return next_lesson.id
    next_module = db.query(Module).filter(Module.order_index > db.get(Module, lesson.module_id).order_index).order_by(Module.order_index).first()
    if not next_module:
        return None
    first = db.query(Lesson).filter(Lesson.module_id == next_module.id).order_by(Lesson.order_index).first()
    return first.id if first else None
