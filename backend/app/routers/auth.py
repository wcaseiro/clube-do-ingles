from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import User, Class, InviteLink, ClassStudent
from ..schemas import LoginRequest, InviteRegisterRequest, Token
from ..security import verify_password, get_password_hash, create_access_token
from ..auth import get_current_user
from ..xp import add_daily_login_xp

router = APIRouter(prefix="/auth", tags=["auth"])

def _public_user(user: User):
    return {"id": user.id, "first_name": user.first_name, "nickname": user.nickname, "role": user.role, "avatar": user.avatar, "level": user.level, "total_xp": user.total_xp}

@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    class_ = db.query(Class).filter(func.lower(Class.code) == data.class_code.lower(), Class.is_active == True).first()
    if not class_:
        raise HTTPException(status_code=401, detail="Turma não encontrada ou inativa")
    user = db.query(User).join(ClassStudent, ClassStudent.user_id == User.id).filter(
        ClassStudent.class_id == class_.id,
        func.lower(User.nickname) == data.nickname.lower(),
        User.is_active == True,
        ClassStudent.status == "active"
    ).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Login inválido")
    user.last_login_at = datetime.utcnow()
    db.add(user)
    db.commit()
    add_daily_login_xp(db, user)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}

@router.post("/register-invite/{code}", response_model=Token)
def register_by_invite(code: str, data: InviteRegisterRequest, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="As senhas não conferem")
    invite = db.query(InviteLink).filter(func.lower(InviteLink.code) == code.lower(), InviteLink.is_active == True).first()
    if not invite or not invite.class_ or not invite.class_.is_active:
        raise HTTPException(status_code=404, detail="Convite inválido ou inativo")
    if invite.max_uses and invite.used_count >= invite.max_uses:
        raise HTTPException(status_code=400, detail="Convite atingiu o limite de usos")
    existing = db.query(User).join(ClassStudent, ClassStudent.user_id == User.id).filter(
        ClassStudent.class_id == invite.class_id,
        func.lower(User.nickname) == data.nickname.lower(),
        ClassStudent.status == "active"
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Esse nickname já está em uso nessa turma")
    user = User(
        first_name=data.first_name.strip().split()[0],
        nickname=data.nickname.strip(),
        password_hash=get_password_hash(data.password),
        role="student",
        avatar=data.avatar or "🦊",
    )
    db.add(user)
    db.flush()
    db.add(ClassStudent(class_id=invite.class_id, user_id=user.id, status="active"))
    invite.used_count = (invite.used_count or 0) + 1
    db.add(invite)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _public_user(user)
