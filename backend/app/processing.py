"""In-process transcription and analysis workflow."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import ActionItem, MeetingSession, SessionStatus, SessionTopic, TranscriptSegment
from app.providers import ProviderFailure, analyze_transcript, transcribe_audio


logger = logging.getLogger(__name__)


def _update_failure(factory: sessionmaker[Session], session_id: UUID, stage: str, code: str) -> None:
    try:
        with factory.begin() as db:
            row = db.get(MeetingSession, session_id)
            if row is not None:
                row.status = SessionStatus.FAILED.value
                row.failed_stage = stage
                row.safe_error_code = code[:80]
                row.updated_at = datetime.now(UTC)
    except Exception as exc:
        logger.error("failed to persist processing failure", extra={"error_type": type(exc).__name__})


def run_processing(
    session_id: UUID,
    settings: Settings,
    factory: sessionmaker[Session],
    start_stage: str = "TRANSCRIBING",
) -> None:
    stage = start_stage
    try:
        with factory.begin() as db:
            row = db.scalar(select(MeetingSession).where(MeetingSession.id == session_id).with_for_update())
            if row is None or row.status not in {SessionStatus.UPLOADED.value, SessionStatus.FAILED.value}:
                return
            if stage == "TRANSCRIBING":
                row.status = SessionStatus.TRANSCRIBING.value
                row.failed_stage = None
                row.safe_error_code = None
                audio_key = row.audio_storage_key
                media_type = row.media_type
            else:
                row.status = SessionStatus.ANALYZING.value
                row.failed_stage = None
                row.safe_error_code = None

        if stage == "TRANSCRIBING":
            audio_path = (settings.resolved_audio_storage_dir / audio_key).resolve()
            root = settings.resolved_audio_storage_dir.resolve()
            if audio_path.parent != root or not audio_path.is_file():
                raise ProviderFailure("stored_audio_missing", "Stored recording is unavailable.")
            transcript_result = transcribe_audio(audio_path.read_bytes(), media_type, settings)
            with factory.begin() as db:
                row = db.get(MeetingSession, session_id)
                if row is None:
                    return
                # Replace the complete transcript in one transaction. Reprocessing
                # the same session never appends duplicate ordinal rows.
                db.execute(delete(TranscriptSegment).where(TranscriptSegment.session_id == session_id))
                db.add_all(
                    [
                        TranscriptSegment(
                            session_id=session_id,
                            ordinal=index,
                            text=part.text,
                            speaker_label=part.speaker_label,
                            start_ms=part.start_ms,
                            end_ms=part.end_ms,
                        )
                        for index, part in enumerate(transcript_result.segments)
                    ]
                )
                row.status = SessionStatus.ANALYZING.value
                row.failed_stage = None
                row.safe_error_code = None
            stage = "ANALYZING"

        with factory() as db:
            row = db.get(MeetingSession, session_id)
            if row is None:
                return
            transcript = "\n".join(
                segment.text
                for segment in db.scalars(
                    select(TranscriptSegment)
                    .where(TranscriptSegment.session_id == session_id)
                    .order_by(TranscriptSegment.ordinal)
                )
            ).strip()
        if not transcript:
            raise ProviderFailure("transcription_empty", "No transcript is available for analysis.")

        analysis = analyze_transcript(transcript, settings)
        with factory.begin() as db:
            row = db.get(MeetingSession, session_id)
            if row is None:
                return
            db.execute(delete(SessionTopic).where(SessionTopic.session_id == session_id))
            db.execute(delete(ActionItem).where(ActionItem.session_id == session_id))
            db.add_all(
                [
                    SessionTopic(session_id=session_id, ordinal=i, title=topic.title, summary=topic.summary)
                    for i, topic in enumerate(analysis.topics)
                ]
            )
            db.add_all(
                [
                    ActionItem(
                        session_id=session_id,
                        ordinal=i,
                        description=item.description,
                        assignee=item.assignee or "Unassigned",
                        due_date=item.due_date,
                        timeframe=item.timeframe,
                        priority=item.priority,
                        is_completed=False,
                    )
                    for i, item in enumerate(analysis.action_items)
                ]
            )
            row.status = SessionStatus.COMPLETED.value
            row.failed_stage = None
            row.safe_error_code = None
            row.completed_at = datetime.now(UTC)
            row.updated_at = datetime.now(UTC)
    except ProviderFailure as exc:
        _update_failure(factory, session_id, stage, exc.code)
        logger.warning("meeting processing failed", extra={"stage": stage, "error_code": exc.code})
    except Exception as exc:
        _update_failure(factory, session_id, stage, f"{stage.lower()}_internal_error")
        logger.error("meeting processing encountered an internal error", extra={"stage": stage, "error_type": type(exc).__name__})
