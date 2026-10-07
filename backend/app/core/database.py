from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import db_models  # noqa: F401

    if engine.dialect.name != "postgresql":
        raise RuntimeError("MedNarrate requires PostgreSQL because RAG uses the pgvector extension.")

    # The database user must be allowed to create extensions. On managed PostgreSQL
    # providers pgvector is commonly pre-approved and this statement is idempotent.
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)

    # HNSW gives fast cosine-neighbor search and requires no training phase.
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_medical_knowledge_embedding_hnsw "
            "ON medical_knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
        ))
