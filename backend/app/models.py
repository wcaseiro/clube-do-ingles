from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(80), nullable=False)
    nickname = Column(String(80), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    avatar = Column(String(80), default="🦊")
    level = Column(String(40), default="Beginner 1")
    total_xp = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    last_login_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    class_links = relationship("ClassStudent", back_populates="user")

class Class(Base):
    __tablename__ = "classes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text)
    level = Column(String(40), default="A1 Beginner")
    code = Column(String(40), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    students = relationship("ClassStudent", back_populates="class_")
    invites = relationship("InviteLink", back_populates="class_")

class InviteLink(Base):
    __tablename__ = "invite_links"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    code = Column(String(80), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    max_uses = Column(Integer)
    used_count = Column(Integer, default=0)
    expires_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    class_ = relationship("Class", back_populates="invites")

class ClassStudent(Base):
    __tablename__ = "class_students"
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="active")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("class_id", "user_id", name="uq_class_user"),)

    class_ = relationship("Class", back_populates="students")
    user = relationship("User", back_populates="class_links")

class Module(Base):
    __tablename__ = "modules"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(120), nullable=False)
    description = Column(Text)
    level = Column(String(20), default="A1")
    order_index = Column(Integer, nullable=False)
    lessons = relationship("Lesson", back_populates="module")

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    title = Column(String(120), nullable=False)
    objective = Column(Text)
    phrase_en = Column(Text)
    phrase_pt = Column(Text)
    example_en = Column(Text)
    example_pt = Column(Text)
    content_json = Column(Text)
    order_index = Column(Integer, nullable=False)
    module = relationship("Module", back_populates="lessons")
    quizzes = relationship("Quiz", back_populates="lesson")

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    question = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    correct_option = Column(String(1), nullable=False)
    explanation = Column(Text)
    lesson = relationship("Lesson", back_populates="quizzes")

class StudentProgress(Base):
    __tablename__ = "student_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    status = Column(String(30), default="not_started")
    score = Column(Integer, default=0)
    completed_at = Column(DateTime)
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),)

class XPEvent(Base):
    __tablename__ = "xp_events"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_type = Column(String(80), nullable=False)
    points = Column(Integer, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AIConversation(Base):
    __tablename__ = "ai_conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"))
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    correction_json = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
