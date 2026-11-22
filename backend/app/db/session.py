from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


engine_options: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine: Engine = create_engine(
    settings.database_url,
    **engine_options,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Iterator[Session]:
    """Provide a SQLAlchemy session for a request or task."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
