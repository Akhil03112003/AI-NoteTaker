"""Create meeting_sessions for persisted audio intake."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_meeting_sessions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meeting_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("audio_storage_key", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="UPLOADED", nullable=False),
        sa.Column("safe_error_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('UPLOADED', 'TRANSCRIBING', 'ANALYZING', 'COMPLETED', 'FAILED')",
            name="ck_meeting_sessions_status",
        ),
        sa.CheckConstraint("file_size_bytes > 0", name="ck_meeting_sessions_file_size_positive"),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_meeting_sessions_duration_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_meeting_sessions"),
        sa.UniqueConstraint("audio_storage_key", name="uq_meeting_sessions_audio_storage_key"),
    )
    op.create_index(
        "ix_meeting_sessions_created_at_id",
        "meeting_sessions",
        ["created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_meeting_sessions_created_at_id", table_name="meeting_sessions")
    op.drop_table("meeting_sessions")
