import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Lesson, AIConversation
from ..auth import get_current_user
from ..schemas import AIChatRequest, AIChatResponse
from ..ai_teacher import generate_ai_response
from ..xp import add_ai_xp_once_per_day

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/chat", response_model=AIChatResponse)
def chat(data: AIChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lesson = db.get(Lesson, data.lesson_id) if data.lesson_id else None
    result = generate_ai_response(data.message, user.first_name, lesson.title if lesson else None)
    points = add_ai_xp_once_per_day(db, user)
    conv = AIConversation(
        user_id=user.id,
        lesson_id=data.lesson_id,
        user_message=data.message,
        ai_response=json.dumps(result, ensure_ascii=False),
        correction_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(conv); db.commit()
    result["points"] = points
    return result

@router.get("/history")
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(AIConversation).filter(AIConversation.user_id == user.id).order_by(AIConversation.created_at.desc()).limit(20).all()
    return [{"message": r.user_message, "ai_response": r.ai_response, "created_at": r.created_at} for r in rows]
