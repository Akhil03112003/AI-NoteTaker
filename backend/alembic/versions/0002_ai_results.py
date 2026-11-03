"""Add transcripts, topic summaries, action items and processing failure stage."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_ai_results"
down_revision = "0001_meeting_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meeting_sessions", sa.Column("failed_stage", sa.String(length=20), nullable=True))
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("speaker_label", sa.String(length=120), nullable=True),
        sa.Column("start_ms", sa.Integer(), nullable=True),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.CheckConstraint("ordinal >= 0", name="ck_transcript_segments_ordinal_nonnegative"),
        sa.CheckConstraint("start_ms IS NULL OR start_ms >= 0", name="ck_transcript_segments_start_nonnegative"),
        sa.CheckConstraint("end_ms IS NULL OR end_ms >= 0", name="ck_transcript_segments_end_nonnegative"),
        sa.ForeignKeyConstraint(["session_id"], ["meeting_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_transcript_segments"),
        sa.UniqueConstraint("session_id", "ordinal", name="uq_transcript_segments_session_ordinal"),
    )
    op.create_index("ix_transcript_segments_session_id", "transcript_segments", ["session_id"])
    op.create_table(
        "session_topics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.String(length=2000), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["meeting_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_session_topics"),
        sa.UniqueConstraint("session_id", "ordinal", name="uq_session_topics_session_ordinal"),
    )
    op.create_index("ix_session_topics_session_id", "session_topics", ["session_id"])
    op.create_table(
        "action_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("assignee", sa.String(length=200), nullable=False, server_default="Unassigned"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("timeframe", sa.String(length=200), nullable=True),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("priority IN ('High', 'Medium', 'Low')", name="ck_action_items_priority"),
        sa.ForeignKeyConstraint(["session_id"], ["meeting_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_action_items"),
        sa.UniqueConstraint("session_id", "ordinal", name="uq_action_items_session_ordinal"),
    )
    op.create_index("ix_action_items_session_id", "action_items", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_action_items_session_id", table_name="action_items")
    op.drop_table("action_items")
    op.drop_index("ix_session_topics_session_id", table_name="session_topics")
    op.drop_table("session_topics")
    op.drop_index("ix_transcript_segments_session_id", table_name="transcript_segments")
    op.drop_table("transcript_segments")
    op.drop_column("meeting_sessions", "failed_stage")
