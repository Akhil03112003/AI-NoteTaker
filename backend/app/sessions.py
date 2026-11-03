"""Session upload and read APIs."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.audio_storage import AudioRejected, StorageUnavailable, delete_stored_audio, sanitize_filename, store_audio
from app.config import Settings
from app.database import get_db
from app.models import ActionItem, MeetingSession, SessionStatus, SessionTopic, TranscriptSegment


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])
action_items_router = APIRouter(prefix="/api/action-items", tags=["action items"])


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _rollback_quietly(db: Session) -> None:
    try:
        db.rollback()
    except Exception:
        pass


def _session_persisted_after_commit_error(
    factory: sessionmaker[Session], session_id: UUID
) -> bool | None:
    """Resolve an ambiguous commit using an independent session when possible."""
    verification_session: Session | None = None
    try:
        verification_session = factory()
        return verification_session.get(MeetingSession, session_id) is not None
    except Exception as exc:
        logger.warning(
            "could not resolve session commit outcome",
            extra={"session_id": str(session_id), "error_type": type(exc).__name__},
        )
        return None
    finally:
        if verification_session is not None:
            try:
                verification_session.close()
            except Exception:
                pass


class SessionCreated(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime


class SessionHistoryItem(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime
    file_size_bytes: int


class SessionHistory(BaseModel):
    items: list[SessionHistoryItem]
    limit: int
    offset: int
    total: int


class SessionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_filename: str
    media_type: str
    file_size_bytes: int
    duration_ms: int | None
    status: str
    created_at: datetime
    updated_at: datetime
    safe_error_code: str | None
    failed_stage: str | None
    transcript_segments: list["TranscriptSegmentOutput"] = []
    topics: list["TopicOutput"] = []
    action_items: list["ActionItemOutput"] = []


class TranscriptSegmentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ordinal: int
    text: str
    speaker_label: str | None
    start_ms: int | None
    end_ms: int | None


class TopicOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ordinal: int
    title: str
    summary: str


class ActionItemOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    ordinal: int
    description: str
    assignee: str
    due_date: date | None
    timeframe: str | None
    priority: str
    is_completed: bool


SessionDetail.model_rebuild()


class ActionItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    description: str = Field(min_length=1, max_length=1000)
    assignee: str = Field(default="Unassigned", min_length=1, max_length=200)
    due_date: date | None = None
    timeframe: str | None = Field(default=None, max_length=200)
    priority: str = Field(default="Medium", pattern="^(High|Medium|Low)$")


class ActionItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    assignee: str | None = Field(default=None, min_length=1, max_length=200)
    due_date: date | None = None
    timeframe: str | None = Field(default=None, max_length=200)
    priority: str | None = Field(default=None, pattern="^(High|Medium|Low)$")
    is_completed: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value):
        if isinstance(value, dict) and any(
            key in value and value[key] is None
            for key in ("description", "assignee", "priority", "is_completed")
        ):
            raise ValueError("required action item fields cannot be null")
        return value


def _safe_title(title: str | None, filename: str) -> str:
    if title and title.strip():
        cleaned = "".join(char for char in title.strip() if ord(char) >= 32 and ord(char) != 127)
        cleaned = cleaned[:200].strip()
        if cleaned:
            return cleaned
    stem = Path(filename).stem
    stem = re.sub(r"[\x00-\x1f\x7f]", "", stem).strip()[:200]
    return stem or "Untitled meeting"


@router.post("", response_model=SessionCreated, status_code=202)
def create_session(
    request: Request,
    background_tasks: BackgroundTasks,
    request_file: Annotated[UploadFile, File(alias="file")],
    title: Annotated[str | None, Form(max_length=200)] = None,
    db: Session = Depends(get_db),
) -> SessionCreated:
    settings: Settings = request.app.state.settings

    session_id = uuid4()
    stored = None
    committed = False
    preserve_audio = False
    try:
        stored = store_audio(
            request_file.file,
            filename=request_file.filename,
            content_type=request_file.content_type,
            storage_root=settings.resolved_audio_storage_dir,
            session_id=session_id,
            max_bytes=settings.max_upload_bytes,
        )
        row = MeetingSession(
            id=session_id,
            title=_safe_title(title, stored.original_filename),
            original_filename=sanitize_filename(stored.original_filename),
            media_type=stored.media_type,
            file_size_bytes=stored.file_size_bytes,
            audio_storage_key=stored.storage_key,
            status=SessionStatus.UPLOADED.value,
        )
        db.add(row)
        db.flush()
        response = SessionCreated(
            id=row.id,
            title=row.title,
            status=row.status,
            created_at=row.created_at,
        )
        # From this point, a raised exception or process interruption may leave
        # commit outcome unknown; preserve audio unless commit is confirmed.
        preserve_audio = True
        try:
            db.commit()
        except Exception:
            persisted = _session_persisted_after_commit_error(
                request.app.state.session_factory, session_id
            )
            if persisted is True:
                # PostgreSQL committed but the acknowledgement was lost. Keep
                # the audio and report the already-persisted session as accepted.
                committed = True
                logger.warning(
                    "session commit acknowledgement was lost after persistence",
                    extra={"session_id": str(session_id)},
                )
                background_tasks.add_task(
                    request.app.state.processor,
                    session_id,
                    settings,
                    request.app.state.session_factory,
                )
                return response
            # A fresh read that sees no row cannot prove the original commit
            # will not finish later. Preserve the file for every unconfirmed
            # commit outcome; an orphan is safer than a dangling DB reference.
            preserve_audio = True
            logger.error(
                "session commit outcome is unresolved; audio file retained",
                extra={"session_id": str(session_id)},
            )
            raise
        committed = True
        preserve_audio = False
        background_tasks.add_task(
            request.app.state.processor,
            session_id,
            settings,
            request.app.state.session_factory,
        )
        return response
    except AudioRejected as exc:
        _rollback_quietly(db)
        raise APIError(exc.status_code, exc.code, exc.message) from None
    except StorageUnavailable:
        _rollback_quietly(db)
        logger.warning("audio storage unavailable", extra={"session_id": str(session_id)})
        raise APIError(503, "storage_or_database_unavailable", "Audio storage is temporarily unavailable.") from None
    except SQLAlchemyError as exc:
        _rollback_quietly(db)
        logger.warning(
            "session persistence failed",
            extra={"session_id": str(session_id), "error_type": type(exc).__name__},
        )
        raise APIError(503, "storage_or_database_unavailable", "Session storage is temporarily unavailable.") from None
    except Exception as exc:
        _rollback_quietly(db)
        logger.error(
            "session intake failed",
            extra={"session_id": str(session_id), "error_type": type(exc).__name__},
        )
        raise APIError(500, "internal_error", "The upload could not be saved.") from None
    finally:
        if not committed:
            _rollback_quietly(db)
            if stored is not None and not preserve_audio:
                delete_stored_audio(settings.resolved_audio_storage_dir, stored.storage_key)


@router.get("", response_model=SessionHistory)
def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SessionHistory:
    try:
        total = db.scalar(select(func.count()).select_from(MeetingSession)) or 0
        rows = db.scalars(
            select(MeetingSession)
            .order_by(MeetingSession.created_at.desc(), MeetingSession.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    except SQLAlchemyError as exc:
        _rollback_quietly(db)
        logger.warning("history query failed", extra={"error_type": type(exc).__name__})
        raise APIError(503, "storage_or_database_unavailable", "Session history is temporarily unavailable.") from None
    return SessionHistory(
        items=[
            SessionHistoryItem(
                id=row.id,
                title=row.title,
                status=row.status,
                created_at=row.created_at,
                file_size_bytes=row.file_size_bytes,
            )
            for row in rows
        ],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: UUID, db: Session = Depends(get_db)) -> SessionDetail:
    try:
        row = db.get(MeetingSession, session_id)
    except SQLAlchemyError as exc:
        _rollback_quietly(db)
        logger.warning("session detail query failed", extra={"error_type": type(exc).__name__})
        raise APIError(503, "storage_or_database_unavailable", "Session details are temporarily unavailable.") from None
    if row is None:
        raise APIError(404, "session_not_found", "No session exists with that ID.")
    try:
        return SessionDetail.model_validate(row)
    except SQLAlchemyError as exc:
        _rollback_quietly(db)
        logger.warning("session results query failed", extra={"error_type": type(exc).__name__})
        raise APIError(503, "storage_or_database_unavailable", "Session results are temporarily unavailable.") from None


@router.post("/{session_id}/action-items", response_model=ActionItemOutput, status_code=201)
def create_action_item(
    session_id: UUID,
    payload: ActionItemCreate,
    db: Session = Depends(get_db),
) -> ActionItemOutput:
    try:
        row = db.get(MeetingSession, session_id)
        if row is None:
            raise APIError(404, "session_not_found", "No session exists with that ID.")
        last_ordinal = db.scalar(
            select(func.max(ActionItem.ordinal)).where(ActionItem.session_id == session_id)
        )
        next_ordinal = (last_ordinal if last_ordinal is not None else -1) + 1
        item = ActionItem(session_id=session_id, ordinal=next_ordinal, **payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return ActionItemOutput.model_validate(item)
    except APIError:
        _rollback_quietly(db)
        raise
    except SQLAlchemyError as exc:
        _rollback_quietly(db)
        logger.warning("action item create failed", extra={"error_type": type(exc).__name__})
        raise APIError(503, "storage_or_database_unavailable", "Action item could not be saved.") from None


@action_items_router.patch("/{action_item_id}", response_model=ActionItemOutput)
def patch_action_item(
    action_item_id: UUID,
    payload: ActionItemPatch,
    db: Session = Depends(get_db),
) -> ActionItemOutput:
    try:
        item = db.get(ActionItem, action_item_id)
        if item is None:
            raise APIError(404, "action_item_not_found", "No action item exists with that ID.")
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise APIError(422, "empty_update", "Provide at least one action item field to update.")
        for key, value in changes.items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return ActionItemOutput.model_validate(item)
    except APIError:
        _rollback_quietly(db)
        raise
    except SQLAlchemyError as exc:
        _rollback_quietly(db)
        logger.warning("action item update failed", extra={"error_type": type(exc).__name__})
        raise APIError(503, "storage_or_database_unavailable", "Action item could not be updated.") from None


@router.post("/{session_id}/retry", status_code=202)
def retry_session(
    session_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str | UUID]:
    try:
        row = db.get(MeetingSession, session_id)
        if row is None:
            raise APIError(404, "session_not_found", "No session exists with that ID.")
        if row.status != SessionStatus.FAILED.value:
            raise APIError(409, "session_not_failed", "Only failed sessions can be retried.")
        stage = row.failed_stage or "TRANSCRIBING"
        if stage not in {"TRANSCRIBING", "ANALYZING"}:
            stage = "TRANSCRIBING"
        if stage == "ANALYZING" and not row.transcript_segments:
            stage = "TRANSCRIBING"
        if stage == "TRANSCRIBING":
            key = row.audio_storage_key
            audio = (request.app.state.settings.resolved_audio_storage_dir / key).resolve()
            if audio.parent != request.app.state.settings.resolved_audio_storage_dir.resolve() or not audio.is_file():
                raise APIError(409, "stored_audio_missing", "The stored recording is unavailable for retry.")
        row.status = SessionStatus.UPLOADED.value
        row.failed_stage = None
        row.safe_error_code = None
        db.commit()
    except APIError:
        _rollback_quietly(db)
        raise
    except SQLAlchemyError as exc:
        _rollback_quietly(db)
        logger.warning("session retry update failed", extra={"error_type": type(exc).__name__})
        raise APIError(503, "storage_or_database_unavailable", "The session could not be queued for retry.") from None
    background_tasks.add_task(
        request.app.state.processor,
        session_id,
        request.app.state.settings,
        request.app.state.session_factory,
        stage,
    )
    return {"id": session_id, "status": SessionStatus.UPLOADED.value}
