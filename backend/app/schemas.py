from pydantic import BaseModel, Field

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class LoginRequest(BaseModel):
    class_code: str
    nickname: str
    password: str

class InviteRegisterRequest(BaseModel):
    first_name: str = Field(min_length=2, max_length=80)
    nickname: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=4, max_length=128)
    confirm_password: str = Field(min_length=4, max_length=128)
    avatar: str | None = "🦊"

class ClassCreate(BaseModel):
    name: str
    description: str | None = None
    level: str = "A1 Beginner"
    code: str

class ClassUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    level: str | None = None
    code: str | None = None
    is_active: bool | None = None

class StudentUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=2, max_length=80)
    nickname: str | None = Field(default=None, min_length=2, max_length=80)
    avatar: str | None = Field(default=None, max_length=80)
    level: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None

class InviteOut(BaseModel):
    code: str
    class_name: str
    class_code: str | None = None
    level: str
    is_active: bool

class UserOut(BaseModel):
    id: int
    first_name: str
    nickname: str
    role: str
    avatar: str | None = None
    level: str | None = None
    total_xp: int = 0
    streak_days: int = 0
    is_active: bool = True

class QuizAnswer(BaseModel):
    answer: str

class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    lesson_id: int | None = None

class AIChatResponse(BaseModel):
    feedback: str
    correction: str | None = None
    explanation_pt: str | None = None
    next_question: str
    points: int = 0
    remaining_today: int | None = None
    used_today: int | None = None
    limit_today: int | None = None
    mood: str | None = None
    topic: str | None = None
    status: str | None = None
    understood: bool | None = None
    needs_repeat: bool | None = None
    source: str | None = None
    fallback: bool | None = None


class AIStartResponse(BaseModel):
    feedback: str
    correction: str | None = None
    explanation_pt: str | None = None
    next_question: str
    points: int = 0
    remaining_today: int | None = None
    used_today: int | None = None
    limit_today: int | None = None
    mood: str | None = None
    topic: str | None = None
    status: str | None = None
    understood: bool | None = None
    needs_repeat: bool | None = None
    source: str | None = None
    fallback: bool | None = None
