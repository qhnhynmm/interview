from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine = create_engine(
    settings.database_url,
    echo=settings.db_echo,
    connect_args=connect_args,
    pool_pre_ping=not is_sqlite,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_interview_cv_columns() -> None:
    inspector = inspect(engine)
    if "interviews" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("interviews")}
    json_type = "JSONB" if not is_sqlite else "JSON"
    statements: list[str] = []
    if "cv_text" not in existing:
        statements.append("ALTER TABLE interviews ADD COLUMN cv_text TEXT")
    if "cv_fields" not in existing:
        statements.append(f"ALTER TABLE interviews ADD COLUMN cv_fields {json_type}")

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def init_db() -> None:
    import app.models  # noqa: F401

    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.removeprefix("sqlite:///")
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    _migrate_interview_cv_columns()