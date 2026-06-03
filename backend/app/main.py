from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .database import Base, engine
from .routers import auth, invites, admin, student, lessons, quizzes, ai, challenges, presence
from .seed import seed

load_dotenv()

app = FastAPI(title="Clube do Inglês API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def startup_event():
    # Seed idempotente para facilitar o MVP.
    seed()

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "clube-do-ingles"}

app.include_router(auth.router, prefix="/api")
app.include_router(invites.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(student.router, prefix="/api")
app.include_router(lessons.router, prefix="/api")
app.include_router(quizzes.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(challenges.router, prefix="/api")

app.include_router(presence.router, prefix="/api")
