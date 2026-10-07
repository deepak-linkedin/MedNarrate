import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    profile: Mapped["UserProfileRecord | None"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)
    reports: Mapped[list["ReportSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserProfileRecord(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (UniqueConstraint("user_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column(Integer)
    education: Mapped[str] = mapped_column(String(120))
    medical_knowledge: Mapped[str] = mapped_column(String(30))
    preferred_language: Mapped[str] = mapped_column(String(50), default="English")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="profile")


class ReportSession(Base):
    __tablename__ = "report_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    age: Mapped[int] = mapped_column(Integer)
    education: Mapped[str] = mapped_column(String(120))
    medical_knowledge: Mapped[str] = mapped_column(String(30))
    preferred_language: Mapped[str] = mapped_column(String(50), default="English")
    status: Mapped[str] = mapped_column(String(30), default="completed")
    interpretation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    narrative_spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    narrative_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    safety_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sources_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user: Mapped[User] = relationship(back_populates="reports")
    findings: Mapped[list["FindingRecord"]] = relationship(back_populates="session", cascade="all, delete-orphan")


# class FindingRecord(Base):
#     __tablename__ = "finding_records"
#     id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
#     session_id: Mapped[str] = mapped_column(ForeignKey("report_sessions.id", ondelete="CASCADE"), index=True)
#     test_name: Mapped[str] = mapped_column(String(160))
#     value: Mapped[str] = mapped_column(String(80))
#     unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
#     reference_range: Mapped[str | None] = mapped_column(String(160), nullable=True)
#     status: Mapped[str] = mapped_column(String(30))
#     session: Mapped[ReportSession] = relationship(back_populates="findings")

class FindingRecord(Base):
    __tablename__ = "finding_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey("report_sessions.id", ondelete="CASCADE"),
        index=True,
    )

    finding_type: Mapped[str] = mapped_column(
        String(30),
        default="other",
    )

    test_name: Mapped[str] = mapped_column(
        String(160),
    )

    value: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    unit: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    reference_range: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
    )

    session: Mapped[ReportSession] = relationship(
        back_populates="findings"
    )


class MedicalKnowledgeChunk(Base):
    """Persistent RAG chunk store backed by PostgreSQL + pgvector."""

    __tablename__ = "medical_knowledge_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(200), index=True)
    source: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(500))
    source_reference: Mapped[str] = mapped_column(String(1000), index=True)
    chunk_id: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    origin: Mapped[str] = mapped_column(String(30), default="local")  # local | online
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
