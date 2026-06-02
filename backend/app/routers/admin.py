import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import User, Class, InviteLink, ClassStudent, StudentProgress, XPEvent, AIConversation
from ..schemas import ClassCreate, ClassUpdate
from ..auth import require_admin
from ..security import get_password_hash

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return {
        "students": db.query(User).filter(User.role == "student", User.is_active == True).count(),
        "classes": db.query(Class).filter(Class.is_active == True).count(),
        "lessons_completed": db.query(StudentProgress).filter(StudentProgress.status == "completed").count(),
        "ai_conversations": db.query(AIConversation).count(),
        "xp_total": db.query(func.coalesce(func.sum(XPEvent.points), 0)).scalar() or 0,
    }

@router.get("/classes")
def list_classes(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    classes = db.query(Class).order_by(Class.created_at.desc()).all()
    return [{"id": c.id, "name": c.name, "description": c.description, "level": c.level, "code": c.code, "is_active": c.is_active, "students": len(c.students)} for c in classes]

@router.post("/classes")
def create_class(data: ClassCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.query(Class).filter(func.lower(Class.code) == data.code.lower()).first():
        raise HTTPException(status_code=400, detail="Código de turma já existe")
    c = Class(name=data.name, description=data.description, level=data.level, code=data.code.upper())
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "name": c.name, "code": c.code}

@router.get("/classes/{class_id}")
def get_class(class_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c = db.get(Class, class_id)
    if not c: raise HTTPException(status_code=404, detail="Turma não encontrada")
    students = db.query(User).join(ClassStudent).filter(ClassStudent.class_id == c.id, ClassStudent.status == "active").all()
    invites = db.query(InviteLink).filter(InviteLink.class_id == c.id).all()
    return {
        "id": c.id, "name": c.name, "description": c.description, "level": c.level, "code": c.code, "is_active": c.is_active,
        "students": [{"id": u.id, "first_name": u.first_name, "nickname": u.nickname, "avatar": u.avatar, "total_xp": u.total_xp, "last_login_at": u.last_login_at} for u in students],
        "invites": [{"id": i.id, "code": i.code, "is_active": i.is_active, "used_count": i.used_count, "max_uses": i.max_uses} for i in invites]
    }

@router.put("/classes/{class_id}")
def update_class(class_id: int, data: ClassUpdate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c = db.get(Class, class_id)
    if not c: raise HTTPException(status_code=404, detail="Turma não encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "code" and v: v = v.upper()
        setattr(c, k, v)
    db.add(c); db.commit(); db.refresh(c)
    return {"ok": True, "class": {"id": c.id, "name": c.name, "code": c.code, "is_active": c.is_active}}

@router.post("/classes/{class_id}/invite")
def create_invite(class_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    c = db.get(Class, class_id)
    if not c: raise HTTPException(status_code=404, detail="Turma não encontrada")
    code = c.code
    if db.query(InviteLink).filter(InviteLink.code == code).first():
        code = f"{c.code}-{secrets.token_hex(3).upper()}"
    invite = InviteLink(class_id=c.id, code=code, is_active=True)
    db.add(invite); db.commit(); db.refresh(invite)
    return {"id": invite.id, "code": invite.code, "link": f"/convite/{invite.code}"}

@router.get("/students")
def list_students(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.query(User, Class).join(ClassStudent, ClassStudent.user_id == User.id).join(Class, Class.id == ClassStudent.class_id).filter(User.role == "student").all()
    return [{"id": u.id, "first_name": u.first_name, "nickname": u.nickname, "avatar": u.avatar, "class_name": c.name, "class_code": c.code, "total_xp": u.total_xp, "level": u.level, "last_login_at": u.last_login_at, "is_active": u.is_active} for u, c in rows]

@router.post("/students/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u or u.role != "student": raise HTTPException(status_code=404, detail="Aluno não encontrado")
    new_pass = secrets.token_urlsafe(6)
    u.password_hash = get_password_hash(new_pass)
    db.add(u); db.commit()
    return {"user_id": u.id, "nickname": u.nickname, "new_password": new_pass}

@router.delete("/students/{user_id}")
def deactivate_student(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if not u or u.role != "student": raise HTTPException(status_code=404, detail="Aluno não encontrado")
    u.is_active = False
    db.add(u); db.commit()
    return {"ok": True}
