import json
import os
from datetime import datetime, time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Lesson, AIConversation
from ..auth import get_current_user
from ..schemas import AIChatRequest, AIChatResponse, AIStartResponse
from ..ai_teacher import generate_ai_response
from ..xp import add_ai_xp_once_per_day

router = APIRouter(prefix="/ai", tags=["ai"])


def _today_bounds():
    today = datetime.utcnow().date()
    return datetime.combine(today, time.min), datetime.combine(today, time.max)


def _daily_usage(db: Session, user_id: int) -> tuple[int, int, int]:
    limit = int(os.getenv("AI_DAILY_LIMIT", "20"))
    start, end = _today_bounds()
    used_today = db.query(AIConversation).filter(
        AIConversation.user_id == user_id,
        AIConversation.created_at >= start,
        AIConversation.created_at <= end,
    ).count()
    remaining = max(0, limit - used_today)
    return used_today, remaining, limit


def _history_rows(db: Session, user_id: int, limit: int | None = None):
    limit = limit or int(os.getenv("AI_CONTEXT_LIMIT", "12"))
    rows = db.query(AIConversation).filter(
        AIConversation.user_id == user_id
    ).order_by(AIConversation.created_at.desc()).limit(limit).all()
    return list(reversed(rows))


def _history_payload(rows):
    return [{"user_message": r.user_message, "ai_response": r.ai_response} for r in rows]


def _usage_payload(db: Session, user_id: int):
    used_today, remaining, limit = _daily_usage(db, user_id)
    percent = round((used_today / limit * 100), 1) if limit else 0
    return {
        "used_today": used_today,
        "remaining_today": remaining,
        "limit_today": limit,
        "usage_percent": percent,
        "provider": os.getenv("AI_PROVIDER", "mock"),
    }


@router.get("/usage")
def usage(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _usage_payload(db, user.id)


@router.post("/start", response_model=AIStartResponse)
def start_conversation(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Start does not consume the daily interaction limit and does not grant XP.
    rows = _history_rows(db, user.id, int(os.getenv("AI_START_CONTEXT_LIMIT", "20")))
    history = _history_payload(rows)
    turn_index = db.query(AIConversation).filter(AIConversation.user_id == user.id).count()

    result = generate_ai_response(
        "__START_CONVERSATION__",
        user.first_name,
        None,
        turn_index=turn_index,
        history=history,
    )

    usage = _usage_payload(db, user.id)
    result.update(usage)
    result["points"] = 0
    return result


@router.post("/chat", response_model=AIChatResponse)
def chat(data: AIChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    used_today, remaining, limit = _daily_usage(db, user.id)

    if used_today >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Limite diário de {limit} interações com a Luma atingido. Volte amanhã para praticar mais.",
        )

    context_limit = int(os.getenv("AI_CONTEXT_LIMIT", os.getenv("AI_HISTORY_LIMIT", "12")))
    lesson = db.get(Lesson, data.lesson_id) if data.lesson_id else None

    recent_rows = _history_rows(db, user.id, context_limit)
    history = _history_payload(recent_rows)
    turn_index = db.query(AIConversation).filter(AIConversation.user_id == user.id).count()

    result = generate_ai_response(
        data.message,
        user.first_name,
        lesson.title if lesson else None,
        turn_index=turn_index,
        history=history,
    )

    points = add_ai_xp_once_per_day(db, user)
    conv = AIConversation(
        user_id=user.id,
        lesson_id=data.lesson_id,
        user_message=data.message,
        ai_response=json.dumps(result, ensure_ascii=False),
        correction_json=json.dumps(result, ensure_ascii=False),
    )
    db.add(conv)
    db.commit()

    result["points"] = points
    result["limit_today"] = limit
    result["used_today"] = used_today + 1
    result["remaining_today"] = max(0, limit - used_today - 1)
    result["usage_percent"] = round(((used_today + 1) / limit * 100), 1) if limit else 0
    return result


@router.get("/history")
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    history_limit = int(os.getenv("AI_HISTORY_LIMIT", "12"))
    rows = _history_rows(db, user.id, history_limit)
    return [{"message": r.user_message, "ai_response": r.ai_response, "created_at": r.created_at} for r in rows]
