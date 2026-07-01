import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from api.config import get_settings

settings = get_settings()


def _ensure_database_exists() -> None:
    url = make_url(settings.app_database_url)
    target_db = url.database
    if not target_db:
        return
    conn = None
    try:
        conn = psycopg2.connect(
            host=url.host or "localhost",
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            dbname="postgres",
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{target_db}"')
                print(f"Created database: {target_db}")
    except Exception as exc:
        print(f"Warning: could not ensure database exists: {exc}")
    finally:
        if conn:
            conn.close()


_ensure_database_exists()

engine = create_engine(settings.app_database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from api.models import AppUser  # noqa: F401
    Base.metadata.create_all(bind=engine)
