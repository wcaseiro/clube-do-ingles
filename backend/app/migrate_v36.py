from sqlalchemy import text
from .database import engine, Base
from . import models  # noqa

def _columns(conn, table):
    try:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {row[1] for row in rows}
    except Exception:
        return set()

def run():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        user_cols = _columns(conn, "users")
        if "last_seen_at" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN last_seen_at DATETIME"))

        challenge_cols = _columns(conn, "challenges")
        if challenge_cols and "accepted_at" not in challenge_cols:
            conn.execute(text("ALTER TABLE challenges ADD COLUMN accepted_at DATETIME"))

if __name__ == "__main__":
    run()
    print("Migrações v3.6 aplicadas.")
