import json
import os
from datetime import datetime, timezone, timedelta, time
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import User, Class, InviteLink, ClassStudent, StudentProgress, XPEvent, AIConversation, Challenge, ChallengeAnswer
from ..schemas import ClassCreate, ClassUpdate, StudentUpdate
from ..auth import require_admin
from ..security import get_password_hash
from ..nickname_guard import validate_nickname_or_raise, validate_first_name_or_raise

router = APIRouter(prefix="/admin", tags=["admin"])


def _read_ai_status():
    path = os.getenv("AI_STATUS_FILE", "/tmp/clube-do-ingles-ai-status.json")
    default = {
        "provider": os.getenv("AI_PROVIDER", "mock"),
        "status": "unknown",
        "message": "Sem status recente da IA.",
        "retry_after_seconds": None,
        "updated_at": None,
    }
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("provider", os.getenv("AI_PROVIDER", "mock"))
        data.setdefault("status", "unknown")
        data.setdefault("message", "")
        data.setdefault("retry_after_seconds", None)
        data.setdefault("updated_at", None)
        return data
    except Exception as exc:
        default["status"] = "error"
        default["message"] = f"Falha ao ler status da IA: {exc}"
        return default


def _student_public(u: User, c: Class | None = None):
    return {
        "id": u.id,
        "first_name": u.first_name,
        "nickname": u.nickname,
        "avatar": u.avatar,
        "class_name": c.name if c else None,
        "class_code": c.code if c else None,
        "total_xp": u.total_xp,
        "level": u.level,
        "last_login_at": u.last_login_at,
        "is_active": u.is_active,
    }

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return {
        "students": db.query(User).filter(User.role == "student", User.is_active == True).count(),
        "students_total": db.query(User).filter(User.role == "student").count(),
        "classes": db.query(Class).filter(Class.is_active == True).count(),
        "lessons_completed": db.query(StudentProgress).filter(StudentProgress.status == "completed").count(),
        "ai_conversations": db.query(AIConversation).count(),
        "xp_total": db.query(func.coalesce(func.sum(XPEvent.points), 0)).scalar() or 0,
        "ai_status": _read_ai_status(),
    }



@router.get("/reports/daily")
def daily_report(date: str | None = None, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if date:
        try:
            day = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Data inválida. Use YYYY-MM-DD.")
    else:
        day = datetime.utcnow().date()

    start = datetime.combine(day, time.min)
    end = datetime.combine(day, time.max)

    students = db.query(User).filter(User.role == "student").order_by(User.first_name).all()
    rows = []

    for u in students:
        conversations = db.query(AIConversation).filter(
            AIConversation.user_id == u.id,
            AIConversation.created_at >= start,
            AIConversation.created_at <= end,
        ).order_by(AIConversation.created_at).all()

        xp_today = db.query(func.coalesce(func.sum(XPEvent.points), 0)).filter(
            XPEvent.user_id == u.id,
            XPEvent.created_at >= start,
            XPEvent.created_at <= end,
        ).scalar() or 0

        answers_today = db.query(ChallengeAnswer).filter(
            ChallengeAnswer.user_id == u.id,
            ChallengeAnswer.created_at >= start,
            ChallengeAnswer.created_at <= end,
        ).all()

        challenges_won = db.query(Challenge).filter(
            Challenge.winner_id == u.id,
            Challenge.completed_at >= start,
            Challenge.completed_at <= end,
        ).count()

        if conversations:
            span = (conversations[-1].created_at - conversations[0].created_at).total_seconds()
            estimated_minutes = max(1, round(span / 60)) if len(conversations) > 1 else 1
        else:
            estimated_minutes = 0

        rows.append({
            "id": u.id,
            "first_name": u.first_name,
            "nickname": u.nickname,
            "avatar": u.avatar,
            "is_active": u.is_active,
            "last_seen_at": u.last_seen_at,
            "online": bool(u.last_seen_at and u.last_seen_at >= datetime.utcnow() - timedelta(minutes=5)),
            "ai_messages": len(conversations),
            "estimated_conversation_minutes": estimated_minutes,
            "xp_today": int(xp_today or 0),
            "challenge_answers": len(answers_today),
            "challenge_correct": sum(1 for a in answers_today if a.is_correct),
            "challenge_wrong": sum(1 for a in answers_today if not a.is_correct),
            "challenges_won": challenges_won,
        })

    return {
        "date": day.isoformat(),
        "students": rows,
        "totals": {
            "students": len(rows),
            "ai_messages": sum(r["ai_messages"] for r in rows),
            "estimated_conversation_minutes": sum(r["estimated_conversation_minutes"] for r in rows),
            "xp_today": sum(r["xp_today"] for r in rows),
            "challenge_answers": sum(r["challenge_answers"] for r in rows),
            "challenges_won": sum(r["challenges_won"] for r in rows),
        }
    }

@router.get("/ai-status")
def ai_status(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    status = _read_ai_status()
    today = datetime.utcnow().date()
    # Informativo: total de chamadas do app hoje, não é o contador oficial da Google/Gemini.
    today_calls = db.query(AIConversation).filter(func.date(AIConversation.created_at) == today.isoformat()).count()
    status["app_ai_calls_today"] = today_calls
    status["provider_configured"] = os.getenv("AI_PROVIDER", "mock")
    return status

@router.get("/classes")
def list_classes(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    classes = db.query(Class).order_by(Class.created_at.desc()).all()
    return [{
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "level": c.level,
        "code": c.code,
        "is_active": c.is_active,
        "students": len([s for s in c.students if s.status == "active"]),
    } for c in classes]

@router.post("/classes")
def create_class(data: ClassCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    code = (data.code or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="Informe o código da turma")
    if db.query(Class).filter(func.lower(Class.code) == code.lower()).first():
        raise HTTPException(status_code=400, detail="Código de turma já existe")
    c = Class(name=data.name.strip(), description=data.description, level=data.level, code=code)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "name": c.name, "code": c.code}

@router.get("/classes/{class_id}")
def get_class(class_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c = db.get(Class, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    students = db.query(User).join(ClassStudent).filter(ClassStudent.class_id == c.id).all()
    invites = db.query(InviteLink).filter(InviteLink.class_id == c.id).all()
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "level": c.level,
        "code": c.code,
        "is_active": c.is_active,
        "students": [_student_public(u, c) for u in students],
        "invites": [{"id": i.id, "code": i.code, "is_active": i.is_active, "used_count": i.used_count, "max_uses": i.max_uses} for i in invites],
    }

@router.put("/classes/{class_id}")
def update_class(class_id: int, data: ClassUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c = db.get(Class, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    values = data.model_dump(exclude_unset=True)
    if "code" in values and values["code"]:
        new_code = values["code"].strip().upper()
        exists = db.query(Class).filter(func.lower(Class.code) == new_code.lower(), Class.id != c.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Código de turma já existe")
        values["code"] = new_code
    for k, v in values.items():
        setattr(c, k, v)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"ok": True, "class": {"id": c.id, "name": c.name, "code": c.code, "is_active": c.is_active}}

@router.post("/classes/{class_id}/invite")
def create_invite(class_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c = db.get(Class, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    code = c.code
    if db.query(InviteLink).filter(InviteLink.code == code).first():
        code = f"{c.code}-{secrets.token_hex(3).upper()}"
    invite = InviteLink(class_id=c.id, code=code, is_active=True)
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return {"id": invite.id, "code": invite.code, "class_code": c.code, "class_name": c.name, "link": f"/convite/{invite.code}"}

@router.get("/students")
def list_students(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(User, Class).join(ClassStudent, ClassStudent.user_id == User.id).join(Class, Class.id == ClassStudent.class_id).filter(User.role == "student").order_by(User.created_at.desc()).all()
    return [_student_public(u, c) for u, c in rows]

@router.get("/students/{user_id}")
def get_student(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    row = db.query(User, Class).join(ClassStudent, ClassStudent.user_id == User.id).join(Class, Class.id == ClassStudent.class_id).filter(User.id == user_id, User.role == "student").first()
    if not row:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    u, c = row
    return _student_public(u, c)

@router.put("/students/{user_id}")
def update_student(user_id: int, data: StudentUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u or u.role != "student":
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    values = data.model_dump(exclude_unset=True)

    if "first_name" in values and values["first_name"] is not None:
        u.first_name = validate_first_name_or_raise(values["first_name"])

    if "nickname" in values and values["nickname"] is not None:
        nickname = validate_nickname_or_raise(values["nickname"])
        links = db.query(ClassStudent).filter(ClassStudent.user_id == u.id).all()
        class_ids = [l.class_id for l in links]
        if class_ids:
            exists = db.query(User).join(ClassStudent, ClassStudent.user_id == User.id).filter(
                ClassStudent.class_id.in_(class_ids),
                func.lower(User.nickname) == nickname.lower(),
                User.id != u.id,
                ClassStudent.status == "active",
            ).first()
            if exists:
                raise HTTPException(status_code=400, detail="Esse nickname já está em uso nessa turma")
        u.nickname = nickname

    if "avatar" in values and values["avatar"] is not None:
        u.avatar = values["avatar"][:80]

    if "level" in values and values["level"] is not None:
        u.level = values["level"][:80]

    if "is_active" in values and values["is_active"] is not None:
        u.is_active = bool(values["is_active"])

    db.add(u)
    db.commit()
    db.refresh(u)
    return {"ok": True, "student": _student_public(u)}

@router.post("/students/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u or u.role != "student":
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    new_pass = secrets.token_urlsafe(6).replace("-", "A").replace("_", "B")[:10]
    u.password_hash = get_password_hash(new_pass)
    db.add(u)
    db.commit()
    return {"user_id": u.id, "nickname": u.nickname, "new_password": new_pass}

@router.post("/students/{user_id}/toggle-active")
def toggle_student(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u or u.role != "student":
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    u.is_active = not bool(u.is_active)
    db.add(u)
    db.commit()
    return {"ok": True, "user_id": u.id, "is_active": u.is_active}

@router.delete("/students/{user_id}")
def deactivate_student(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u or u.role != "student":
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    u.is_active = False
    db.add(u)
    db.commit()
    return {"ok": True, "user_id": u.id, "is_active": u.is_active}
