from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.audio_storage import AudioRejected, delete_stored_audio, store_audio
from app.config import BACKEND_DIR, Settings, get_settings
from app.database import make_engine, make_session_factory
from app.main import create_app
from app.models import MeetingSession, SessionStatus


PROJECT_ROOT = BACKEND_DIR.parent
SAMPLE_WAV = PROJECT_ROOT / "samples" / "deepgram-test.wav"
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def _database_setup():
    settings = get_settings()
    if settings.test_database_url is None:
        pytest.exit("TEST_DATABASE_URL is required in backend/.env or the process environment.")

    development_url = make_url(settings.database_url.get_secret_value())
    test_url = make_url(settings.test_database_url.get_secret_value())
    if development_url.database != "ai_notetaker":
        pytest.exit("DATABASE_URL must target the configured development database ai_notetaker.")
    if test_url.database != "ai_notetaker_test" or test_url.database == development_url.database:
        pytest.exit("TEST_DATABASE_URL must target the separate ai_notetaker_test database.")
    if development_url.username != "ai_notetaker_app" or test_url.username != "ai_notetaker_app":
        pytest.exit("Both database URLs must use the configured application role.")
    if test_url.drivername != "postgresql+psycopg":
        pytest.exit("TEST_DATABASE_URL must use the PostgreSQL psycopg driver.")

    development_engine = make_engine(settings.database_url.get_secret_value())
    try:
        with development_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        pytest.exit(f"Development PostgreSQL connection failed ({type(exc).__name__}); details omitted.")
    finally:
        development_engine.dispose()

    engine = make_engine(settings.test_database_url.get_secret_value())
    try:
        with engine.connect() as connection:
            existing_tables = set(inspect(connection).get_table_names())
        expected_tables = {
            "alembic_version", "meeting_sessions", "transcript_segments", "session_topics", "action_items"
        }
        unexpected_tables = existing_tables - expected_tables
        if unexpected_tables:
            pytest.exit("Test database has unexpected tables; refusing destructive test setup.")
        if "meeting_sessions" in existing_tables and "alembic_version" not in existing_tables:
            pytest.exit("Test database has an unmanaged session table; refusing migration setup.")

        config = Config(str(ALEMBIC_INI))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            command.check(config)

        return settings, engine, make_session_factory(engine)
    except SQLAlchemyError as exc:
        engine.dispose()
        pytest.exit(f"Test PostgreSQL setup failed ({type(exc).__name__}); details omitted.")
    except Exception:
        engine.dispose()
        raise


@pytest.fixture(scope="session")
def database_setup():
    return _database_setup()


@pytest.fixture(autouse=True)
def clean_dedicated_test_database(database_setup):
    _, engine, _ = database_setup
    # Exact database-name and dev/test separation checks run before this DELETE.
    with engine.begin() as connection:
        connection.execute(delete(MeetingSession))
    yield
    with engine.begin() as connection:
        connection.execute(delete(MeetingSession))


@pytest.fixture(scope="session", autouse=True)
def dispose_test_engine(database_setup):
    yield
    database_setup[1].dispose()


@pytest.fixture
def client_factory(database_setup, tmp_path):
    base_settings, _, factory = database_setup

    def build(*, max_bytes: int | None = None, storage_dir: Path | None = None, db_factory=None):
        settings = base_settings.model_copy(
            update={
                "audio_storage_dir": storage_dir or (tmp_path / f"audio-{uuid4().hex}"),
                "max_upload_bytes": max_bytes or base_settings.max_upload_bytes,
                "cors_origins": "http://localhost:5173",
            }
        )
        app = create_app(settings, session_factory=db_factory or factory, processor=lambda *args: None)
        return TestClient(app), settings

    return build


def _fake_audio(extension: str) -> tuple[bytes, str]:
    if extension == ".wav":
        return b"RIFF\x18\x00\x00\x00WAVEfmt " + b"0" * 20, "audio/wav"
    if extension == ".mp3":
        return b"ID3" + b"0" * 20, "audio/mpeg"
    if extension == ".m4a":
        return b"\x00\x00\x00\x18ftypM4A " + b"0" * 20, "audio/mp4"
    return b"\x1a\x45\xdf\xa3" + b"0" * 20, "audio/webm"


@pytest.mark.parametrize("extension", [".mp3", ".wav", ".m4a", ".webm"])
def test_storage_accepts_supported_formats_and_uses_generated_name(tmp_path, extension):
    content, content_type = _fake_audio(extension)
    session_id = uuid4()
    stored = store_audio(
        BytesIO(content),
        filename=f"meeting{extension}",
        content_type=content_type,
        storage_root=tmp_path,
        session_id=session_id,
        max_bytes=1024,
    )

    assert stored.storage_key == f"{session_id.hex}{extension}"
    assert stored.media_type in {"audio/mpeg", "audio/wav", "audio/mp4", "audio/webm"}
    assert stored.path.parent == tmp_path.resolve()
    assert stored.path.read_bytes() == content
    assert delete_stored_audio(tmp_path, stored.storage_key)
    assert not stored.path.exists()


def test_storage_rejects_empty_mismatched_and_oversized_audio(tmp_path):
    with pytest.raises(AudioRejected) as empty:
        store_audio(
            BytesIO(b""), filename="empty.wav", content_type="audio/wav",
            storage_root=tmp_path, session_id=uuid4(), max_bytes=100,
        )
    assert empty.value.code == "empty_audio"

    with pytest.raises(AudioRejected) as mismatch:
        store_audio(
            BytesIO(b"not audio"), filename="wrong.wav", content_type="audio/wav",
            storage_root=tmp_path, session_id=uuid4(), max_bytes=100,
        )
    assert mismatch.value.code == "invalid_audio_signature"

    audio, mime = _fake_audio(".wav")
    with pytest.raises(AudioRejected) as oversized:
        store_audio(
            BytesIO(audio), filename="large.wav", content_type=mime,
            storage_root=tmp_path, session_id=uuid4(), max_bytes=8,
        )
    assert oversized.value.code == "upload_too_large"
    assert list(tmp_path.iterdir()) == []


def test_storage_rejects_mime_and_path_traversal_never_controls_path(tmp_path):
    wav, _ = _fake_audio(".wav")
    with pytest.raises(AudioRejected) as mismatch:
        store_audio(
            BytesIO(wav), filename="voice.wav", content_type="text/plain",
            storage_root=tmp_path, session_id=uuid4(), max_bytes=1024,
        )
    assert mismatch.value.code == "unsupported_audio_type"

    session_id = uuid4()
    stored = store_audio(
        BytesIO(wav), filename=r"..\..\outside\safe.wav", content_type="audio/wav",
        storage_root=tmp_path, session_id=session_id, max_bytes=1024,
    )
    assert stored.original_filename == "safe.wav"
    assert stored.path.parent == tmp_path.resolve()
    assert stored.storage_key == f"{session_id.hex}.wav"


def test_settings_env_precedence_and_secret_masking(tmp_path, monkeypatch):
    env_file = tmp_path / "settings.env"
    env_file.write_text(
        "DATABASE_URL=postgresql+psycopg://file_user:file_password@localhost:5432/from_file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://process_user:process_password@localhost:5432/from_process",
    )
    settings = Settings(_env_file=env_file)
    assert settings.database_url.get_secret_value().endswith("/from_process")
    assert "process_password" not in repr(settings)
    assert "file_password" not in repr(settings)


def test_relative_storage_path_is_independent_of_working_directory(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://user:pass@localhost/db")
    expected = (Path(os.environ["LOCALAPPDATA"]) / "ai-notetaker" / "uploads").resolve()
    monkeypatch.chdir(tmp_path)
    assert settings.resolved_audio_storage_dir == expected


def test_storage_path_expands_local_app_data_setting(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local App Data"))
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:pass@localhost/db",
        audio_storage_dir=r"%LOCALAPPDATA%\ai-notetaker\uploads",
    )
    assert settings.resolved_audio_storage_dir == (tmp_path / "Local App Data" / "ai-notetaker" / "uploads").resolve()


def test_status_vocabulary_is_exact():
    assert {status.value for status in SessionStatus} == {
        "UPLOADED", "TRANSCRIBING", "ANALYZING", "COMPLETED", "FAILED"
    }


def test_health_is_liveness_only(client_factory):
    client, _ = client_factory()
    with client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_only_configured_origin(client_factory):
    client, _ = client_factory()
    with client:
        allowed = client.options(
            "/api/sessions",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        denied = client.options(
            "/api/sessions",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert denied.headers.get("access-control-allow-origin") is None


def test_wav_upload_persists_to_postgres_and_detail_hides_storage_key(client_factory, database_setup):
    _, _, factory = database_setup
    wav = SAMPLE_WAV.read_bytes()
    client, settings = client_factory()
    with client:
        created = client.post(
            "/api/sessions",
            files={"file": ("planning.wav", wav, "audio/wav")},
            data={"title": " Planning review "},
        )
        assert created.status_code == 202
        created_body = created.json()
        assert created_body["status"] == "UPLOADED"
        assert created_body["title"] == "Planning review"

        session_id = created_body["id"]
        listed = client.get("/api/sessions", params={"limit": 50, "offset": 0})
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["id"] == session_id

        detail = client.get(f"/api/sessions/{session_id}")
        assert detail.status_code == 200
        assert detail.json()["original_filename"] == "planning.wav"
        assert "audio_storage_key" not in detail.json()
        assert str(settings.resolved_audio_storage_dir) not in detail.text

    with factory() as db:
        row = db.get(MeetingSession, UUID(session_id))
        assert row is not None
        assert row.status == SessionStatus.UPLOADED.value
        assert row.file_size_bytes == len(wav)
        audio_path = settings.resolved_audio_storage_dir / row.audio_storage_key
        assert audio_path.read_bytes() == wav


def test_upload_errors_leave_no_rows_or_files(client_factory, database_setup):
    _, engine, _ = database_setup
    client, settings = client_factory()
    with client:
        empty = client.post("/api/sessions", files={"file": ("empty.wav", b"", "audio/wav")})
        invalid = client.post("/api/sessions", files={"file": ("bad.wav", b"not wav", "audio/wav")})
        unsupported = client.post("/api/sessions", files={"file": ("bad.txt", b"abc", "text/plain")})
    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "empty_audio"
    assert invalid.status_code == 415
    assert invalid.json()["error"]["code"] == "invalid_audio_signature"
    assert unsupported.status_code == 415
    assert unsupported.json()["error"]["code"] == "unsupported_audio_type"
    assert list(settings.resolved_audio_storage_dir.glob("*")) == []
    with engine.connect() as connection:
        assert connection.scalar(select(text("count(*)")).select_from(MeetingSession.__table__)) == 0


def test_oversized_upload_is_rejected_and_cleaned(client_factory):
    wav, _ = _fake_audio(".wav")
    client, settings = client_factory(max_bytes=16)
    with client:
        response = client.post("/api/sessions", files={"file": ("large.wav", wav, "audio/wav")})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "upload_too_large"
    assert list(settings.resolved_audio_storage_dir.glob("*")) == []


def test_storage_failure_returns_safe_error(client_factory, tmp_path):
    blocked_path = tmp_path / "not_a_directory"
    blocked_path.write_text("file", encoding="utf-8")
    wav, _ = _fake_audio(".wav")
    client, _ = client_factory(storage_dir=blocked_path)
    with client:
        response = client.post("/api/sessions", files={"file": ("voice.wav", wav, "audio/wav")})
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "storage_or_database_unavailable",
            "message": "Audio storage is temporarily unavailable.",
        }
    }


def test_database_flush_failure_rolls_back_and_removes_audio(client_factory, database_setup, caplog):
    _, engine, _ = database_setup

    class FailingFlushSession(Session):
        def flush(self, *args, **kwargs):
            raise SQLAlchemyError("private-error-marker")

    failing_factory = sessionmaker(bind=engine, class_=FailingFlushSession, autoflush=False)
    wav, _ = _fake_audio(".wav")
    client, settings = client_factory(db_factory=failing_factory)
    with client:
        response = client.post("/api/sessions", files={"file": ("voice.wav", wav, "audio/wav")})
    assert response.status_code == 503
    assert "private-error-marker" not in response.text
    assert "private-error-marker" not in caplog.text
    assert list(settings.resolved_audio_storage_dir.glob("*")) == []
    with engine.connect() as connection:
        count = connection.scalar(select(text("count(*)")).select_from(MeetingSession.__table__))
    assert count == 0


def test_unconfirmed_commit_failure_preserves_audio(client_factory, database_setup):
    _, engine, _ = database_setup

    class UnconfirmedCommitSession(Session):
        def commit(self):
            raise SQLAlchemyError("private-commit-marker")

    unconfirmed_factory = sessionmaker(bind=engine, class_=UnconfirmedCommitSession, autoflush=False)
    verification_factory = sessionmaker(bind=engine, autoflush=False)
    wav, _ = _fake_audio(".wav")
    client, settings = client_factory(db_factory=unconfirmed_factory)
    with client:
        response = client.post("/api/sessions", files={"file": ("voice.wav", wav, "audio/wav")})

    assert response.status_code == 503
    assert "private-commit-marker" not in response.text
    files = list(settings.resolved_audio_storage_dir.glob("*"))
    assert len(files) == 1
    assert files[0].read_bytes() == wav
    with verification_factory() as db:
        assert db.scalar(select(text("count(*)")).select_from(MeetingSession.__table__)) == 0


def test_lost_commit_acknowledgement_keeps_persisted_audio(client_factory, database_setup):
    _, engine, _ = database_setup

    class CommitThenRaiseSession(Session):
        def commit(self):
            super().commit()
            raise RuntimeError("private-acknowledgement-marker")

    commit_then_raise_factory = sessionmaker(
        bind=engine, class_=CommitThenRaiseSession, autoflush=False, expire_on_commit=False
    )
    verification_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    wav, _ = _fake_audio(".wav")
    client, settings = client_factory(db_factory=commit_then_raise_factory)
    with client:
        response = client.post("/api/sessions", files={"file": ("voice.wav", wav, "audio/wav")})

    assert response.status_code == 202
    assert "private-acknowledgement-marker" not in response.text
    session_id = UUID(response.json()["id"])
    with verification_factory() as db:
        row = db.get(MeetingSession, session_id)
    assert row is not None
    audio_path = settings.resolved_audio_storage_dir / row.audio_storage_key
    assert audio_path.read_bytes() == wav


def test_history_pagination_and_newest_first(client_factory, database_setup):
    _, _, factory = database_setup
    now = datetime.now(UTC)
    ids = [uuid4() for _ in range(3)]
    with factory.begin() as db:
        for index, session_id in enumerate(ids):
            db.add(
                MeetingSession(
                    id=session_id,
                    title=f"Session {index}",
                    original_filename=f"{index}.wav",
                    media_type="audio/wav",
                    file_size_bytes=10,
                    audio_storage_key=f"{session_id.hex}.wav",
                    status=SessionStatus.UPLOADED.value,
                    created_at=now + timedelta(seconds=index),
                )
            )

    client, _ = client_factory()
    with client:
        first_page = client.get("/api/sessions", params={"limit": 2, "offset": 0})
        second_page = client.get("/api/sessions", params={"limit": 2, "offset": 2})
        invalid_limit = client.get("/api/sessions", params={"limit": 101})
    assert first_page.status_code == 200
    assert first_page.json()["total"] == 3
    assert [item["id"] for item in first_page.json()["items"]] == [str(ids[2]), str(ids[1])]
    assert [item["id"] for item in second_page.json()["items"]] == [str(ids[0])]
    assert invalid_limit.status_code == 422
    assert "request_validation_error" in invalid_limit.text


def test_session_detail_unknown_and_invalid_uuid(client_factory):
    client, _ = client_factory()
    with client:
        unknown = client.get(f"/api/sessions/{uuid4()}")
        invalid = client.get("/api/sessions/not-a-uuid")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "session_not_found"
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "request_validation_error"


def test_migration_schema_and_alembic_metadata_parity(database_setup):
    _, engine, _ = database_setup
    inspector = inspect(engine)
    assert "meeting_sessions" in inspector.get_table_names()
    assert "alembic_version" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("meeting_sessions")}
    assert {
        "id", "title", "original_filename", "media_type", "file_size_bytes",
        "duration_ms", "audio_storage_key", "status", "created_at", "updated_at",
    } <= columns
    constraints = {item["name"] for item in inspector.get_check_constraints("meeting_sessions")}
    assert {
        "ck_meeting_sessions_status",
        "ck_meeting_sessions_file_size_positive",
        "ck_meeting_sessions_duration_nonnegative",
    } <= constraints
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == "0002_ai_results"
    assert {"transcript_segments", "session_topics", "action_items"} <= set(inspector.get_table_names())
