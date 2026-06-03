import json
import random
import re
from datetime import datetime, timedelta, time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import User, Class, ClassStudent, Lesson, Quiz, Challenge, ChallengeItem, ChallengeAnswer, XPEvent
from ..auth import get_current_user
from ..schemas import ChallengeCreate, ChallengeSubmitAnswer, ChallengeAccept
from ..xp import add_xp

router = APIRouter(prefix="/challenges", tags=["challenges"])

XP_CHALLENGE_PLAY = 15
XP_CHALLENGE_WIN = 60
ONLINE_WINDOW_MINUTES = 5

def _current_class(db: Session, user: User):
    link = db.query(ClassStudent).filter(ClassStudent.user_id == user.id, ClassStudent.status == "active").first()
    if not link:
        return None
    return db.get(Class, link.class_id)

def _class_user_ids(db: Session, class_id: int):
    return [row.user_id for row in db.query(ClassStudent).filter(ClassStudent.class_id == class_id, ClassStudent.status == "active").all()]

def _is_online(user: User):
    if not user.last_seen_at:
        return False
    return user.last_seen_at >= datetime.utcnow() - timedelta(minutes=ONLINE_WINDOW_MINUTES)

def _today_bounds():
    today = datetime.utcnow().date()
    return datetime.combine(today, time.min), datetime.combine(today, time.max)

def _clean(text: str):
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\sáéíóúâêôãõç]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

def _is_correct(answer: str, expected: str, alt: str | None = None):
    a = _clean(answer)
    e = _clean(expected)
    altc = _clean(alt or "")
    if not a:
        return False
    if a == e or (altc and a == altc):
        return True
    if len(e) > 8 and (e in a or a in e):
        return True
    return False

def _item_public(item: ChallengeItem, answer: ChallengeAnswer | None = None):
    options = None
    if item.options_json:
        try:
            options = json.loads(item.options_json)
        except Exception:
            options = None
    return {
        "id": item.id,
        "lesson_id": item.lesson_id,
        "type": item.item_type,
        "prompt": item.prompt,
        "options": options,
        "order_index": item.order_index,
        "answered": bool(answer),
        "answer_text": answer.answer_text if answer else None,
        "is_correct": answer.is_correct if answer else None,
    }

def _challenge_public(db: Session, ch: Challenge, user: User, include_items: bool = False):
    challenger = db.get(User, ch.challenger_id)
    opponent = db.get(User, ch.opponent_id)
    my_score = ch.challenger_score if user.id == ch.challenger_id else ch.opponent_score
    other_score = ch.opponent_score if user.id == ch.challenger_id else ch.challenger_score
    other = opponent if user.id == ch.challenger_id else challenger

    items_payload = []
    if include_items:
        items = db.query(ChallengeItem).filter(ChallengeItem.challenge_id == ch.id).order_by(ChallengeItem.order_index).all()
        answers = db.query(ChallengeAnswer).filter(ChallengeAnswer.challenge_id == ch.id, ChallengeAnswer.user_id == user.id).all()
        by_item = {a.item_id: a for a in answers}
        items_payload = [_item_public(item, by_item.get(item.id)) for item in items]

    return {
        "id": ch.id,
        "status": ch.status,
        "created_at": ch.created_at,
        "accepted_at": ch.accepted_at,
        "completed_at": ch.completed_at,
        "challenger": {"id": challenger.id, "nickname": challenger.nickname, "avatar": challenger.avatar, "online": _is_online(challenger)} if challenger else None,
        "opponent": {"id": opponent.id, "nickname": opponent.nickname, "avatar": opponent.avatar, "online": _is_online(opponent)} if opponent else None,
        "other_player": {"id": other.id, "nickname": other.nickname, "avatar": other.avatar, "online": _is_online(other)} if other else None,
        "am_challenger": user.id == ch.challenger_id,
        "am_opponent": user.id == ch.opponent_id,
        "my_score": my_score or 0,
        "other_score": other_score or 0,
        "challenger_score": ch.challenger_score or 0,
        "opponent_score": ch.opponent_score or 0,
        "winner_id": ch.winner_id,
        "i_won": ch.winner_id == user.id if ch.winner_id else None,
        "items": items_payload,
        "summary": json.loads(ch.summary_json) if ch.summary_json else None,
    }

def _make_options(correct_text: str, wrong1: str, wrong2: str, seed: str):
    rows = [correct_text, wrong1, wrong2]
    rng = random.Random(seed)
    rng.shuffle(rows)
    labels = ["A", "B", "C"]
    options = {labels[i]: rows[i] for i in range(3)}
    correct_label = next(k for k, v in options.items() if v == correct_text)
    return options, correct_label

def _build_items(db: Session, challenge_id: int, class_id: int, seed: str):
    lessons = db.query(Lesson).order_by(Lesson.id).all()
    if not lessons:
        raise HTTPException(status_code=400, detail="Não há lições cadastradas para montar o desafio")

    rng = random.Random(seed)
    selected = lessons[:]
    rng.shuffle(selected)
    selected = selected[:10] if len(selected) >= 10 else selected

    all_phrases = [l.phrase_en for l in lessons if l.phrase_en]
    items = []

    for idx, lesson in enumerate(selected, start=1):
        quiz = db.query(Quiz).filter(Quiz.lesson_id == lesson.id).first()
        kind = ["choose_correct", "write_en", "speak_en", "translate_pt_to_en", "translate_en_to_pt"][(idx - 1) % 5]

        if kind == "choose_correct" and quiz:
            correct = {"A": quiz.option_a, "B": quiz.option_b, "C": quiz.option_c}.get(quiz.correct_option.upper(), quiz.option_a)
            wrongs = [quiz.option_a, quiz.option_b, quiz.option_c]
            wrongs = [w for w in wrongs if w != correct]
            while len(wrongs) < 2:
                wrongs.append(rng.choice(all_phrases) if all_phrases else "I am happy.")
            options, correct_label = _make_options(correct, wrongs[0], wrongs[1], f"{seed}:{idx}")
            prompt = quiz.question
            expected = correct_label
            expected_alt = correct
            item_type = "choose_correct"
        elif kind == "translate_pt_to_en":
            prompt = f"Traduza para inglês: {lesson.phrase_pt or lesson.title}"
            expected = lesson.phrase_en or ""
            expected_alt = None
            options = None
            item_type = "translate_pt_to_en"
        elif kind == "translate_en_to_pt":
            prompt = f"Traduza para português: {lesson.phrase_en or lesson.title}"
            expected = lesson.phrase_pt or ""
            expected_alt = None
            options = None
            item_type = "translate_en_to_pt"
        elif kind == "speak_en":
            prompt = f"Fale em inglês: {lesson.phrase_pt or lesson.title}"
            expected = lesson.phrase_en or ""
            expected_alt = None
            options = None
            item_type = "speak_en"
        else:
            prompt = f"Escreva em inglês: {lesson.phrase_pt or lesson.title}"
            expected = lesson.phrase_en or ""
            expected_alt = None
            options = None
            item_type = "write_en"

        items.append(ChallengeItem(
            challenge_id=challenge_id,
            lesson_id=lesson.id,
            item_type=item_type,
            prompt=prompt,
            expected_answer=expected,
            expected_alt=expected_alt,
            options_json=json.dumps(options, ensure_ascii=False) if options else None,
            order_index=idx,
        ))

    db.add_all(items)
    db.commit()

@router.post("/heartbeat")
def heartbeat_alias(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.last_seen_at = datetime.utcnow()
    db.add(user)
    db.commit()
    return {"ok": True, "last_seen_at": user.last_seen_at}

@router.get("/students")
def students_for_challenge(online_only: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _current_class(db, user)
    if not c:
        return []
    user.last_seen_at = datetime.utcnow()
    db.add(user)
    db.commit()

    user_ids = _class_user_ids(db, c.id)
    rows = db.query(User).filter(User.id.in_(user_ids), User.id != user.id, User.is_active == True, User.role == "student").order_by(User.nickname).all()
    out = []
    for u in rows:
        online = _is_online(u)
        if online_only and not online:
            continue
        out.append({"id": u.id, "nickname": u.nickname, "first_name": u.first_name, "avatar": u.avatar, "total_xp": u.total_xp, "online": online, "last_seen_at": u.last_seen_at})
    return out

@router.post("")
def create_challenge(data: ChallengeCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _current_class(db, user)
    if not c:
        raise HTTPException(status_code=400, detail="Você não está em uma turma ativa")
    opponent = db.get(User, data.opponent_id)
    if not opponent or opponent.role != "student" or not opponent.is_active:
        raise HTTPException(status_code=404, detail="Aluno desafiado não encontrado")
    if opponent.id == user.id:
        raise HTTPException(status_code=400, detail="Escolha outro aluno para desafiar")

    start, end = _today_bounds()
    today_count = db.query(Challenge).filter(
        Challenge.challenger_id == user.id,
        Challenge.created_at >= start,
        Challenge.created_at <= end,
    ).count()
    if today_count >= 1:
        raise HTTPException(status_code=429, detail="Você já enviou um desafio hoje. Amanhã poderá desafiar de novo.")

    allowed = set(_class_user_ids(db, c.id))
    if opponent.id not in allowed:
        raise HTTPException(status_code=400, detail="O aluno precisa estar na mesma turma")

    if not _is_online(opponent):
        raise HTTPException(status_code=400, detail="Esse aluno não está online agora. Escolha alguém online para desafiar.")

    ch = Challenge(class_id=c.id, challenger_id=user.id, opponent_id=opponent.id, status="pending")
    db.add(ch)
    db.commit()
    db.refresh(ch)

    _build_items(db, ch.id, c.id, f"challenge:{ch.id}:{user.id}:{opponent.id}")
    return _challenge_public(db, ch, user, include_items=True)

@router.get("")
def list_challenges(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.last_seen_at = datetime.utcnow()
    db.add(user)
    db.commit()

    rows = db.query(Challenge).filter(
        (Challenge.challenger_id == user.id) | (Challenge.opponent_id == user.id)
    ).order_by(Challenge.created_at.desc()).limit(40).all()
    return [_challenge_public(db, ch, user, include_items=False) for ch in rows]

@router.get("/pending")
def pending_challenges(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(Challenge).filter(Challenge.opponent_id == user.id, Challenge.status == "pending").order_by(Challenge.created_at.desc()).all()
    return [_challenge_public(db, ch, user, include_items=False) for ch in rows]

@router.post("/{challenge_id}/accept")
def accept_challenge(challenge_id: int, data: ChallengeAccept, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ch = db.get(Challenge, challenge_id)
    if not ch or ch.opponent_id != user.id:
        raise HTTPException(status_code=404, detail="Desafio não encontrado")
    if ch.status != "pending":
        raise HTTPException(status_code=400, detail="Esse desafio não está pendente")

    if not data.accept:
        ch.status = "declined"
        db.add(ch)
        db.commit()
        return _challenge_public(db, ch, user, include_items=False)

    ch.status = "active"
    ch.accepted_at = datetime.utcnow()
    db.add(ch)
    db.commit()
    return _challenge_public(db, ch, user, include_items=True)

@router.get("/ranking")
def challenge_ranking(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _current_class(db, user)
    if not c:
        return []
    user_ids = _class_user_ids(db, c.id)
    if not user_ids:
        return []
    rows = db.query(
        User,
        func.count(Challenge.id).label("wins")
    ).outerjoin(Challenge, (Challenge.winner_id == User.id) & (Challenge.status == "completed")).filter(
        User.id.in_(user_ids), User.is_active == True
    ).group_by(User.id).order_by(func.count(Challenge.id).desc(), User.total_xp.desc()).all()

    return [{
        "position": i + 1,
        "id": u.id,
        "nickname": u.nickname,
        "avatar": u.avatar,
        "wins": int(wins or 0),
        "total_xp": u.total_xp or 0,
        "online": _is_online(u),
    } for i, (u, wins) in enumerate(rows)]

@router.get("/{challenge_id}")
def get_challenge(challenge_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ch = db.get(Challenge, challenge_id)
    if not ch or user.id not in (ch.challenger_id, ch.opponent_id):
        raise HTTPException(status_code=404, detail="Desafio não encontrado")
    return _challenge_public(db, ch, user, include_items=True)

def _recalc_challenge(db: Session, ch: Challenge):
    items = db.query(ChallengeItem).filter(ChallengeItem.challenge_id == ch.id).all()
    total = len(items)
    challenger_answers = db.query(ChallengeAnswer).filter(ChallengeAnswer.challenge_id == ch.id, ChallengeAnswer.user_id == ch.challenger_id).all()
    opponent_answers = db.query(ChallengeAnswer).filter(ChallengeAnswer.challenge_id == ch.id, ChallengeAnswer.user_id == ch.opponent_id).all()

    ch.challenger_score = sum(1 for a in challenger_answers if a.is_correct)
    ch.opponent_score = sum(1 for a in opponent_answers if a.is_correct)

    if len(challenger_answers) >= total and len(opponent_answers) >= total:
        ch.status = "completed"
        ch.completed_at = datetime.utcnow()
        if ch.challenger_score > ch.opponent_score:
            ch.winner_id = ch.challenger_id
        elif ch.opponent_score > ch.challenger_score:
            ch.winner_id = ch.opponent_id
        else:
            ch.winner_id = None
        ch.summary_json = json.dumps({
            "total": total,
            "challenger_score": ch.challenger_score,
            "opponent_score": ch.opponent_score,
            "winner_id": ch.winner_id,
        }, ensure_ascii=False)
    db.add(ch)
    db.commit()

@router.post("/{challenge_id}/answers")
def submit_answer(challenge_id: int, data: ChallengeSubmitAnswer, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ch = db.get(Challenge, challenge_id)
    if not ch or user.id not in (ch.challenger_id, ch.opponent_id):
        raise HTTPException(status_code=404, detail="Desafio não encontrado")
    if ch.status == "pending":
        raise HTTPException(status_code=400, detail="Aguarde o aluno aceitar o desafio.")
    if ch.status == "declined":
        raise HTTPException(status_code=400, detail="Esse desafio foi recusado.")
    if ch.status == "completed":
        raise HTTPException(status_code=400, detail="Desafio já finalizado")

    item = db.get(ChallengeItem, data.item_id)
    if not item or item.challenge_id != ch.id:
        raise HTTPException(status_code=404, detail="Questão não encontrada")

    existing = db.query(ChallengeAnswer).filter(ChallengeAnswer.item_id == item.id, ChallengeAnswer.user_id == user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Essa questão já foi respondida")

    answer = (data.answer_text or "").strip()

    if item.item_type == "choose_correct":
        correct = answer.upper() == item.expected_answer.upper()
    else:
        correct = _is_correct(answer, item.expected_answer, item.expected_alt)

    ans = ChallengeAnswer(
        challenge_id=ch.id,
        item_id=item.id,
        user_id=user.id,
        answer_text=answer,
        is_correct=correct,
    )
    db.add(ans)
    db.commit()

    existing_xp = db.query(XPEvent).filter(
        XPEvent.user_id == user.id,
        XPEvent.event_type == f"challenge_play_{ch.id}",
    ).first()
    if not existing_xp:
        add_xp(db, user, f"challenge_play_{ch.id}", XP_CHALLENGE_PLAY, f"Participou do desafio #{ch.id}")

    _recalc_challenge(db, ch)
    db.refresh(ch)

    if ch.status == "completed" and ch.winner_id:
        existing_win = db.query(XPEvent).filter(
            XPEvent.user_id == ch.winner_id,
            XPEvent.event_type == f"challenge_win_{ch.id}",
        ).first()
        if not existing_win:
            winner = db.get(User, ch.winner_id)
            if winner:
                add_xp(db, winner, f"challenge_win_{ch.id}", XP_CHALLENGE_WIN, f"Venceu o desafio #{ch.id}")

    return {
        "correct": correct,
        "expected_answer": item.expected_alt or item.expected_answer,
        "challenge": _challenge_public(db, ch, user, include_items=True),
    }
