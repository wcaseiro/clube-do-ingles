from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Lesson, Quiz, StudentProgress
from ..auth import get_current_user
from ..schemas import QuizAnswer
from ..xp import add_xp, XP_QUIZ_COMPLETED, XP_QUIZ_BONUS

router = APIRouter(tags=["quizzes"])

@router.get("/lessons/{lesson_id}/quiz")
def get_quiz(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    return {
        "id": q.id,
        "lesson_id": q.lesson_id,
        "question": q.question,
        "options": {"A": q.option_a, "B": q.option_b, "C": q.option_c},
        "hint": "Leia a situação e escolha a melhor frase em inglês.",
    }

@router.post("/lessons/{lesson_id}/quiz/answer")
def answer_quiz(lesson_id: int, data: QuizAnswer, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Aula não encontrada")
    q = db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")

    answer = data.answer.upper().strip()
    correct = answer == q.correct_option.upper()
    progress = db.query(StudentProgress).filter(
        StudentProgress.user_id == user.id,
        StudentProgress.lesson_id == lesson_id,
    ).first()
    was_already_passed = progress and (progress.score or 0) >= 80

    if not progress:
        progress = StudentProgress(user_id=user.id, lesson_id=lesson_id, status="in_progress")

    if correct:
        progress.score = 100
    else:
        progress.score = max(progress.score or 0, 0)
    db.add(progress)
    db.commit()

    points = 0
    if correct and not was_already_passed:
        points += add_xp(db, user, "quiz_completed", XP_QUIZ_COMPLETED, f"Quiz correto da aula {lesson.title}")
        points += add_xp(db, user, "quiz_bonus", XP_QUIZ_BONUS, "Bônus por acerto no quiz obrigatório")

    selected_text = {"A": q.option_a, "B": q.option_b, "C": q.option_c}.get(answer, "")
    correct_text = {"A": q.option_a, "B": q.option_b, "C": q.option_c}.get(q.correct_option.upper(), "")

    return {
        "correct": correct,
        "points": points,
        "selected_option": answer,
        "selected_text": selected_text,
        "correct_option": q.correct_option,
        "correct_text": correct_text,
        "explanation": q.explanation,
        "lesson_completed_unlocked": correct,
        "feedback_title": "Muito bem!" if correct else "Quase isso!",
        "feedback_message": "Resposta certa! Missão liberada." if correct else "Ainda não foi dessa vez. Leia com calma e tente outra opção.",
    }
