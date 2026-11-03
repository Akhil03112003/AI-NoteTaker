"""Database models for persisted meeting session intake."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SessionStatus(StrEnum):
    UPLOADED = "UPLOADED"
    TRANSCRIBING = "TRANSCRIBING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MeetingSession(Base):
    __tablename__ = "meeting_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('UPLOADED', 'TRANSCRIBING', 'ANALYZING', 'COMPLETED', 'FAILED')",
            name="ck_meeting_sessions_status",
        ),
        CheckConstraint("file_size_bytes > 0", name="ck_meeting_sessions_file_size_positive"),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_meeting_sessions_duration_nonnegative",
        ),
        PrimaryKeyConstraint("id", name="pk_meeting_sessions"),
        UniqueConstraint("audio_storage_key", name="uq_meeting_sessions_audio_storage_key"),
        Index("ix_meeting_sessions_created_at_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    audio_storage_key: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SessionStatus.UPLOADED.value,
        server_default=SessionStatus.UPLOADED.value,
    )
    safe_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_stage: Mapped[str | None] = mapped_column(String(20), nullable=True)

    transcript_segments: Mapped[list[TranscriptSegment]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="TranscriptSegment.ordinal"
    )
    topics: Mapped[list[SessionTopic]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="SessionTopic.ordinal"
    )
    action_items: Mapped[list[ActionItem]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ActionItem.ordinal"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_transcript_segments_session_ordinal"),
        CheckConstraint("ordinal >= 0", name="ck_transcript_segments_ordinal_nonnegative"),
        CheckConstraint("start_ms IS NULL OR start_ms >= 0", name="ck_transcript_segments_start_nonnegative"),
        CheckConstraint("end_ms IS NULL OR end_ms >= 0", name="ck_transcript_segments_end_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("meeting_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    speaker_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session: Mapped[MeetingSession] = relationship(back_populates="transcript_segments")


class SessionTopic(Base):
    __tablename__ = "session_topics"
    __table_args__ = (UniqueConstraint("session_id", "ordinal", name="uq_session_topics_session_ordinal"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("meeting_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    session: Mapped[MeetingSession] = relationship(back_populates="topics")


class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_action_items_session_ordinal"),
        CheckConstraint("priority IN ('High', 'Medium', 'Low')", name="ck_action_items_priority"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("meeting_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    assignee: Mapped[str] = mapped_column(String(200), nullable=False, default="Unassigned")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(200), nullable=True)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    session: Mapped[MeetingSession] = relationship(back_populates="action_items")
