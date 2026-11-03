# Backend Milestone Plan: Session Intake and History

**Status:** Backend implementation complete. Latest user-confirmed real app run completed through Deepgram and OmniRoute with PostgreSQL persistence; older blocked status below is historical and superseded.  
**Target:** Day 1 backend milestone for the AI Notetaker assignment  
**Plan layout decision:** Option B selected by the user: compact, separated modules; full milestone scope retained  
**Updated:** 2026-11-03

> Historical planning artifact: sections below describe the original Day 1 backend scope and discovery snapshot, not current implementation status. Current source, the latest user-confirmed real end-to-end result, and current API/storage behavior are summarized in [CODEX_HANDOFF.md](CODEX_HANDOFF.md). Current audio default is `%LOCALAPPDATA%\ai-notetaker\uploads`.

This plan follows the approved architecture in [IMPLEMENTATION_STRATEGY.md](IMPLEMENTATION_STRATEGY.md). It covers the FastAPI, configuration, PostgreSQL, Alembic, session model, upload/storage, history/detail, and backend test foundation only. It does not include transcription or AI analysis.

## 1. Scope and current evidence

### In scope

1. FastAPI application foundation and a small liveness endpoint.
2. Centralized, validated backend settings from `backend/.env` and process environment.
3. Synchronous SQLAlchemy 2.x access to PostgreSQL.
4. Alembic migration environment and the first migration.
5. A `meeting_sessions` model using the already approved status vocabulary.
6. Multipart audio intake for the assignment's four file extensions.
7. Private, local, generated-name audio file storage.
8. Paginated session history and session detail routes.
9. API/storage/database tests.

### Explicitly out of scope

- Deepgram calls, transcription, OmniRoute calls, summaries, action-item extraction, background jobs, retries, or transitions beyond initial `UPLOADED`.
- Transcript, topic, and action-item tables. They belong to the later processing milestone.
- React/TypeScript UI, browser MediaRecorder, frontend API client, WebSockets, authentication, collaboration, and meeting integrations.
- Git initialization, deployment, object storage, Redis, a durable worker queue, audio conversion, or a public audio download route.

The existing assignment strategy's `POST /api/sessions` contract uses `202 Accepted`; retain that response and return `UPLOADED`. This milestone accepts and persists the recording but does not start processing.

### Historical project evidence at plan creation

- `backend/` currently contains `scripts/test_deepgram.py` and `.env`; no application, DB, migration, dependency manifest, or test source was found. `frontend/` has no application source.
- The root `.gitignore` already excludes `backend/uploads/`, so use that as the default storage root. Do not expose it as static content.
- The existing virtual environment currently has Pydantic 2.14.2 and HTTPX 0.28.1. FastAPI, SQLAlchemy, Alembic, `psycopg`, `psycopg2-binary`, `pydantic-settings`, `python-multipart`, pytest, and Uvicorn were not installed when inspected. Previously recorded context lists Python 3.12.6, Deepgram SDK 7.16.0, and python-dotenv 1.2.4.
- Deepgram prerecorded WAV succeeded according to the project record. This does not verify this app's upload path. OmniRoute remains unverified and is deferred to the AI stage.
- PostgreSQL TCP availability is verified, but database authentication is not: service `postgresql-x64-18` is running and `pg_isready -h localhost -p 5432` reports accepting connections. A no-password `psql` probe failed with `fe_sendauth: no password supplied`. No development/test databases were created. No `TODOS.md` exists in the project file listing.
- `backend/.env` exists. Its contents were not read; no key value is included here. Keep it as-is and out of Git.

### Historical implementation attempt record (2026-11-02)

- Python environment inspection completed: Python 3.12.6; Pydantic 2.14.2, HTTPX 0.28.1, Deepgram SDK 7.16.0, and python-dotenv 1.2.4 present. FastAPI, Uvicorn, SQLAlchemy, Alembic, psycopg/psycopg2, pydantic-settings, python-multipart, and pytest absent.
- PostgreSQL 18 Windows service is running; port 5432 accepts connections. `psql -w -h localhost -p 5432 -d postgres -c 'SELECT 1;'` failed with `fe_sendauth: no password supplied`. Process-level `DATABASE_URL`, `TEST_DATABASE_URL`, and `PGPASSWORD` variables are unset. The `.env` file was not read, printed, overwritten, or exposed.
- Docker CLI is installed, but Docker daemon is unavailable: the Docker engine named pipe does not exist.
- **Gate outcome at that point:** work was stopped before the backend implementation began. This gate was later resolved; see the runtime verification record at the end. No SQLite substitution was made.
- Migration, tests, application startup, health, upload, history, and detail checks were not run because implementation did not begin.

## 2. Approved shape and file responsibilities

The user's B selection keeps each durable concern in a small module and combines route contracts with the session routes. It avoids a separate repository/service layer that would only forward calls in this milestone.

| Planned path | Responsibility |
| --- | --- |
| `backend/requirements.txt` | Runtime and test dependencies needed to reproduce the backend environment. Keep it to dependencies this app actually imports. |
| `backend/app/__init__.py` | Explicit Python package marker. |
| `backend/app/main.py` | Create FastAPI app, register router and CORS allowlist, liveness route, and safe request-error handling. |
| `backend/app/config.py` | One Pydantic Settings model, cached accessor, absolute `.env` path, path/size/CORS defaults, and masked secret fields for later provider use. |
| `backend/app/database.py` | Declarative base, one process-wide SQLAlchemy engine/session factory, and request-scoped `get_db` dependency. |
| `backend/app/models.py` | `MeetingSession` ORM mapping and exact status enum/check constraint. |
| `backend/app/sessions.py` | `/api/sessions` router, request/response Pydantic schemas, input validation, DB operations, and HTTP mapping. No provider logic. |
| `backend/app/audio_storage.py` | Bounded chunked copy, format/signature checks, generated storage name, path containment check, atomic temp-file promotion, and cleanup. |
| `backend/alembic.ini` | Migration command configuration; do not put a real DB URL here. |
| `backend/alembic/env.py` | Load centralized settings and `MeetingSession` metadata; run offline/online migration paths. |
| `backend/alembic/versions/0001_create_meeting_sessions.py` | Explicit, reviewable initial schema migration. |
| `backend/.env.example` | Names and clearly fake/empty placeholders only; no live values. |
| `backend/tests/test_sessions.py` | Pytest fixtures and API/storage/database integration cases; keep fixtures local here until reuse justifies a `conftest.py`. |

The selected arrangement is compact, but still gives the upload path one storage owner and one DB transaction owner. Do not add a generic service/repository layer unless implementation reveals genuinely shared behavior.

## 3. Dependencies and configuration

### Dependency gate

Before implementation, check the existing Python version and installed distributions once more, then add a small `backend/requirements.txt`. The current environment observation is evidence, not a reason to reinstall already available packages. The app needs:

- Runtime: `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2,<3`, `alembic`, `psycopg[binary]`, `pydantic-settings`, `python-multipart`.
- Retain dependencies needed by the existing smoke script: `deepgram-sdk`, `python-dotenv`; HTTPX is already present and is also used by FastAPI's test client.
- Tests: `pytest`.

Do not add an OmniRoute SDK, audio conversion package, async DB driver, container framework, or testing plugin in this milestone. OmniRoute will be tested for actual gateway/model compatibility during the AI milestone.

Install only the manifest into the existing root `.venv`; do not create a second venv. The configuration implementation should use `pydantic-settings` `BaseSettings` and `SettingsConfigDict`. Pin tested versions or use narrow major-version bounds in the manifest; do not assume the currently present Pydantic minor version is compatible with every future FastAPI release without checking resolver output.

### Settings contract

Use `backend/app/config.py` as the only application configuration source. Resolve `backend/.env` from the module/project location, not the current working directory, so starting from the repository root or `backend/` behaves the same. Process environment variables override `.env`. Cache one settings object for normal app use; let tests inject settings or override dependencies.

Settings to define now:

| Setting | Purpose and validation |
| --- | --- |
| `DATABASE_URL` | Required PostgreSQL URL using the installed psycopg 3 dialect, such as `postgresql+psycopg://...`; fail early with the setting name only if absent. |
| `AUDIO_STORAGE_DIR` | Current default: `%LOCALAPPDATA%\ai-notetaker\uploads`; configured paths expand environment variables and resolve independently of the working directory. |
| `MAX_UPLOAD_BYTES` | Positive integer cap. Use a provisional 25 MiB local default only after checking assignment sample sizes and current Deepgram request limits; treat the number as a configurable engineering default, not an assignment requirement. |
| `CORS_ORIGINS` | Exact local frontend origins for the later Vite client; empty or loopback-only by default. No wildcard with credentials. |
| `DEEPGRAM_API_KEY`, `OMNIROUTE_API_KEY` | Optional masked secret settings for later server-side use. Do not call either provider in this milestone; never include the values in logs, exceptions, settings repr, API responses, or this plan. |
| `OMNIROUTE_BASE_URL`, `OMNIROUTE_MODEL` | Optional non-secret future integration settings. No connectivity claim is made here. |

`backend/.env.example` should list the variable names and dummy/empty values only. Never replace or dump `backend/.env`. Do not put provider keys in `VITE_` variables. Settings validation must not print Pydantic's `input` values; report only the field name and a safe error category.

## 4. Database model and migration

### `meeting_sessions`

Use a UUID primary key generated in the application, timezone-aware UTC timestamps, SQLAlchemy 2-style typed mappings, and a named Alembic migration. Initial columns:

| Column | Type / rule | Why |
| --- | --- | --- |
| `id` | UUID, primary key | Stable public session identifier and storage-name seed. |
| `title` | `VARCHAR(200)`, not null | History label. Default to a sanitized filename stem or `Untitled meeting`; allow an optional multipart title field. |
| `original_filename` | `VARCHAR(255)`, not null | Sanitized display metadata only; never used as a filesystem path. |
| `media_type` | `VARCHAR(100)`, not null | Normalized accepted MIME type for display/processing handoff. |
| `file_size_bytes` | `BIGINT`, positive check | Actual number of bytes copied, not the untrusted `Content-Length`. |
| `duration_ms` | nullable integer | Unknown at intake; transcription/provider stage can fill it later. |
| `audio_storage_key` | relative generated key, not null, unique | Points to private local file; never return this or an absolute path over the API. |
| `status` | `VARCHAR(20)`, not null, check constraint | Exact allowed values: `UPLOADED`, `TRANSCRIBING`, `ANALYZING`, `COMPLETED`, `FAILED`. Create new records as `UPLOADED` only in this milestone. |
| `safe_error_code` | nullable short string | Reserved for later failed processing; no provider response/body or secret. |
| `created_at`, `updated_at` | timezone-aware UTC, not null | History ordering and future updates. |
| `completed_at` | nullable timezone-aware UTC | Future pipeline completion. |

Index history ordering by `created_at` (and use `id` as a deterministic tie-break). Do not add transcript, topic, or action-item tables now. Do not call SQLAlchemy `metadata.create_all()` at app startup; schema changes go through Alembic. Keep transaction scope short and one SQLAlchemy `Session` per request, committed/rolled back and closed by the dependency.

Represent status in Python as a string enum and use a named SQL `CHECK` constraint over the five exact values. This avoids managing a separately created PostgreSQL enum type during the first migration while preserving the approved state vocabulary. The initial route only writes `UPLOADED`.

### Alembic setup

1. Point `alembic.ini` at `backend/alembic` and omit a real connection string from it.
2. In `env.py`, obtain the URL from centralized settings without printing it, import `Base` and `MeetingSession`, set `target_metadata`, and support offline SQL plus online migration execution.
3. Generate or author the initial migration, then inspect it. It should create the table, named constraints, index, and reverse them in dependency-safe order in `downgrade()`.
4. Run `upgrade head` against an explicitly named development database. Run `alembic check` after upgrade to detect model/migration drift.
5. Verify a clean upgrade from an empty test database. Never point a test reset/drop command at the user's development DB.

## 5. Audio intake, storage, and API contracts

### Upload pipeline

```text
multipart request
  -> FastAPI UploadFile (python-multipart; bounded parser/spool behavior)
  -> validate filename extension + MIME allowlist + basic file signature
  -> copy in bounded chunks while counting actual bytes
  -> write private <uuid>.<ext>.part under AUDIO_STORAGE_DIR
  -> flush/close, then atomic rename to <uuid>.<ext>
  -> insert MeetingSession(status=UPLOADED, storage_key, metadata)
  -> commit DB transaction
  -> return 202 with public session metadata

Any validation/storage/DB failure:
  -> rollback DB transaction if open
  -> remove .part/final file created for this request when possible
  -> return a safe error code; never expose a local path or credentials
```

The filesystem and PostgreSQL cannot participate in one atomic transaction. Write to a unique temp file, promote atomically on the same filesystem, then insert/commit the row. If DB persistence fails, delete the promoted file. A process crash between file promotion and DB commit can leave an orphan; document it and defer a reconciler/cleanup command unless observed during implementation. Conversely, do not commit a row before a file is safely stored.

Use an extension allowlist `.mp3`, `.wav`, `.m4a`, `.webm` and matching accepted MIME families; accept common WAV/MP3 aliases and `audio/webm`/`video/webm` where browser output requires it. MIME and filename are untrusted. Add lightweight magic/header checks for RIFF/WAVE, MP4 `ftyp`, WebM EBML, and MP3 ID3/frame headers; this catches obvious mismatches but does not prove the file decodes. Decoder/provider validation remains for the later AI stage. Do not convert audio here.

Generate storage names from a UUID and allowed normalized extension. Strip both slash styles/control characters from display filenames, cap title/name lengths, and never derive a path from user input. Resolve the target and assert it remains beneath the configured storage root. Use restrictive local directory permissions where the OS supports them; on Windows rely on the project's user-only directory ACL. Keep the directory out of static mounts and API responses.

Count copied bytes in fixed chunks (for example, 1 MiB) and reject when the configured cap is exceeded. Check `Content-Length` early when available, but do not trust it instead of counting bytes. Clean up partial files on oversize, invalid signature, write failure, or DB failure. FastAPI parses multipart before entering the route, so the application cap bounds persisted/copied audio but does not alone bound all request parser temporary storage; keep the development server loopback-only and revisit request-body limits before public deployment.

### API contracts

Base prefix is `/api`; JSON error envelope is `{"error":{"code":"...","message":"..."}}`. Messages are safe and actionable, with no path, header, key, provider body, or stack trace.

#### `POST /api/sessions`

- Content type: `multipart/form-data`.
- Required field: `file`.
- Optional field: `title` (trimmed, max 200 chars; otherwise derived safely from the filename).
- Success: `202 Accepted`.
- Response:

```json
{
  "id": "<uuid>",
  "title": "Quarterly planning",
  "status": "UPLOADED",
  "created_at": "<UTC timestamp>"
}
```

- `400 empty_audio`, `413 upload_too_large`, `415 unsupported_audio_type` or `invalid_audio_signature`, `422` for malformed/missing multipart fields, and `503 storage_or_database_unavailable` for a temporary persistence outage. Normalize FastAPI validation errors into the shared envelope without echoing submitted values.

#### `GET /api/sessions?limit=50&offset=0`

- `limit`: default 50, range 1–100. `offset`: default 0, minimum 0.
- Stable newest-first ordering by `created_at DESC, id DESC`.
- Return `{"items":[...],"limit":50,"offset":0,"total":N}`; each item contains `id`, `title`, `status`, `created_at`, and optionally `file_size_bytes`.
- Empty history returns `items: []`, `total: 0`. No search/filter is needed in this milestone.

#### `GET /api/sessions/{session_id}`

- Accept UUID path values. Valid unknown IDs return `404 session_not_found`; malformed IDs are `422`.
- Return `id`, `title`, `original_filename`, `media_type`, `file_size_bytes`, nullable `duration_ms`, `status`, `created_at`, `updated_at`, and nullable safe error code.
- Do not return local storage key/path. Transcript/topic/action-item fields are added when those models exist in the AI milestone; this endpoint is metadata-only while status is `UPLOADED`.

#### `GET /health`

Small liveness response only; it does not claim PostgreSQL is ready. Database readiness is verified by migration and integration tests. Keep Uvicorn bound to `127.0.0.1` during local development.

### Database/file consistency and failure mapping

| Failure | Required behavior |
| --- | --- |
| Missing/empty file | Return a stable client error; no row or file. |
| Unsupported extension, MIME, or obvious signature mismatch | Return 415; remove temp file; no row. |
| File crosses actual byte cap | Return 413; remove temp file; no row. |
| Disk full/permission/read failure | Roll back; remove partial output if possible; safe 503/500 envelope; log request/session ID and error category only. |
| PostgreSQL unavailable/constraint/commit failure | Roll back/close session, remove file from this request, return safe 503/500. Do not log the database URL or secret values. |
| History DB error | Safe 503; do not return SQL/driver text. |
| Client disconnect during upload | Close uploaded temp object and remove app-created partial/final file; no committed row. |
| Process crash between filesystem and DB commit | Possible orphan file; bounded residual risk, no false `UPLOADED` row. Cleanup/reconciliation is deferred. |

No automatic retries for DB writes in this milestone. A retry can create another session; future frontend should disable double-submit and preserve the local Blob. Server-side idempotency is not required for the single-user local MVP.

## 6. Implementation order and dependencies

Do these in order; later work depends on earlier work.

1. **Environment/manifest gate.** Confirm Python executable and current packages; create the minimal `requirements.txt`; install only missing declared packages in the existing `.venv`. Confirm PostgreSQL is available and create separate development and test databases. Never print environment contents.
2. **Configuration.** Add settings, safe validation, root-independent `.env` path, storage path resolution, upload bound, and CORS allowlist. Add `.env.example` without secrets; preserve `.env`.
3. **DB session/base.** Create sync PostgreSQL engine and request-scoped SQLAlchemy session lifecycle. Do not connect on module import if it can be avoided; connections occur on request/migration.
4. **Model.** Add typed `MeetingSession` with constraints/indexes and exact status choices.
5. **Migration.** Configure Alembic metadata and write initial migration. Upgrade a clean local development DB and compare migration state to metadata.
6. **Storage helper.** Implement extension/MIME/signature checks, bounded streaming copy, generated path, containment, atomic rename, and cleanup. Test it with a temporary directory before routing through it.
7. **FastAPI app and upload route.** Register `/health` and `POST /api/sessions`; validate before DB insert, store then commit, compensate file on commit failure, return 202.
8. **History/detail routes.** Add bounded pagination, deterministic ordering, safe serialization, and 404 behavior.
9. **Test database + API tests.** Use `TEST_DATABASE_URL` pointing at a dedicated database whose name clearly ends in `_test`. Run migrations there; refuse destructive cleanup if it is the configured development database. Inject a temporary storage directory. Never use SQLite as the only persistence proof.
10. **Hardening and handoff.** Run all commands below, inspect API schemas/errors, review `.gitignore` (already covers `backend/uploads/` and `.env`), and update project docs with measured results. No Git initialization.

## 7. Test plan and acceptance criteria

Pytest is not installed in the observed environment, so add it as a project test dependency. Use FastAPI `TestClient`/HTTPX and a real PostgreSQL test database for persistence behavior. Use temporary directories and a PostgreSQL dependency override or test session factory; do not mock away the database in every API test.

| Test group | Assertions that catch a real regression |
| --- | --- |
| Settings | Required DB setting fails with a safe field-only message; relative storage config resolves consistently from different working directories; positive upload bound; secret fields are masked in repr/output. |
| Storage unit | Generated name ignores traversal filename; path remains under temp root; valid WAV sample accepted; wrong extension/MIME/signature rejected; empty file rejected; exact cap accepted and cap+1 rejected; failed copy leaves no `.part`/final file. |
| Upload API + PostgreSQL | Multipart WAV returns 202/UUID/UPLOADED; a fresh DB session reads matching metadata; audio bytes are stored under generated private path; original filename never controls path. |
| Upload errors | Missing field/empty file, unsupported extension, mismatched signature, oversize, DB commit failure, and storage failure return expected status/error envelope and leave no row/orphan for handled failure. |
| History/detail | Empty list; correct total; limit/offset validation; newest-first deterministic order; detail serialization omits storage key/path; valid missing UUID returns 404; malformed ID returns 422. |
| Migration | Upgrade from empty test DB; expected table/constraints/index exist; `alembic check` reports no drift. Do not rely on `create_all()`. |
| App boundary | `/health` responds without leaking settings; CORS only permits configured origins; no static route exposes audio. |

Acceptance means: app imports and serves locally, an Alembic-created PostgreSQL schema accepts a multipart file and persists its metadata, the audio is retrievable only from the private storage directory by backend code, history/detail work after a new DB session, all tests pass against the dedicated test database, and errors do not leak local paths, SQL details, or credentials. Do not mark any of these complete until observed.

## 8. Three-day execution plan

The backend foundation should take roughly **9–12 focused engineering hours** if PostgreSQL can be started locally. This is a planning estimate, not measured project velocity. Keep Day 3 available for the assignment's AI/frontend/demo path; if PostgreSQL setup expands beyond half a day, cut polish before cutting persistence tests.

### Day 1: environment, app, and database (about 3–4 hours)

1. Recheck runtime; create the small dependency manifest and install missing declared packages only.
2. Confirm a local PostgreSQL server and create a development DB plus a separate test DB.
3. Implement config, app factory/liveness, sync SQLAlchemy lifecycle, `MeetingSession`, and Alembic setup/migration.
4. Run clean `upgrade head`, inspect schema, and verify Alembic metadata parity.

**Deliverable:** app imports, settings load without exposing values, and a clean PostgreSQL database reaches migration head.

### Day 2: private upload and read APIs (about 4–5 hours)

1. Implement/test storage helper, configured byte cap, type/signature checks, atomic promotion, and cleanup.
2. Implement multipart upload with 202/UPLOADED and transaction compensation.
3. Implement history pagination and detail lookup/404.
4. Exercise manual curl uploads with the curated WAV sample and inspect stored metadata (never inspect `.env`).

**Deliverable:** upload creates one persisted `UPLOADED` session and private audio file; history/detail read it after reconnect.

### Day 3: failure-path verification and handoff (about 2–3 hours for this milestone)

1. Run storage and API/database tests on the dedicated test DB.
2. Exercise oversize, invalid type/signature, invalid UUID, unknown session, and injected storage/DB failure cleanup.
3. Run clean migration check, tests, and local API commands. Record actual results in `PROJECT_PROGRESS.md` and `PROJECT_CONTEXT.md` after implementation, not during this planning-only turn.
4. Hand off to the next milestone: Deepgram app adapter and transcription, then verify OmniRoute application/model compatibility during AI implementation. React/TypeScript follows the approved plan; no UI is part of this backend milestone.

**Deliverable:** passing backend suite and reproducible local commands, or an explicit blocker with the failed command and safe error category. This does not complete the assignment or claim any provider integration beyond the separately verified Deepgram smoke test.

## 9. Verification commands (for implementation time)

Run from PowerShell. These are future verification commands; none were run in this planning session.

```powershell
Set-Location C:\Users\akhil\OneDrive\Desktop\Project\ai-notetaker\backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
..\.venv\Scripts\python.exe -m alembic -c alembic.ini check
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir . --host 127.0.0.1 --port 8000
```

In a second PowerShell window, from the project root:

```powershell
curl.exe -i http://127.0.0.1:8000/health
curl.exe -i -F "file=@samples/deepgram-test.wav" http://127.0.0.1:8000/api/sessions
curl.exe -sS "http://127.0.0.1:8000/api/sessions?limit=50&offset=0"
curl.exe -sS http://127.0.0.1:8000/api/sessions/<returned-uuid>
```

Before pytest, set `TEST_DATABASE_URL` in the test process to the dedicated test DB; do not put it in a command line if the local password would be exposed in shell history. The tests should fail clearly if it is missing or aliases the development DB. Do not run destructive migration/reset commands against a non-test database.

## 10. Risks and controls

| Risk | Control / remaining limit |
| --- | --- |
| Core dependencies and PostgreSQL are absent/unverified in the observed environment | Day 1 begins with a bounded environment/DB gate. Use only manifest dependencies; record a blocker if PostgreSQL cannot be started. |
| Deepgram accepts the tested WAV but not every assignment format/browser recording | Intake performs basic extension/MIME/signature checks only. Verify all formats and actual MediaRecorder output with Deepgram during the later processing/frontend milestones. |
| Multipart parser may spool before endpoint limit runs | Enforce counted file-byte cap and loopback-only local serving; set deployment request-body limits before exposing publicly. |
| Filesystem and DB commit are not atomic together | Temp file + atomic rename + DB insert/commit + compensation cleanup; crash orphan remains a documented low-volume local MVP risk. |
| Spoofed filename/MIME | Generated UUID path, allowlist, signature sniff, sanitized display metadata, no path return. Signature is not full decoder validation. |
| Database URL or provider key appears in errors/logs | Secret settings, safe validation error formatter, no settings dumps/HTTP headers/body logging, verify logs with fake invalid config only. Never print real values. |
| Unsupported browser MIME or codec | Accept assignment formats and common WebM labels; record actual browser MIME later; no conversion in this milestone. |
| User retries/double submits | No server idempotency in this MVP; one upload always creates one session. Frontend later disables duplicate submission and retains its Blob. |
| Three-day deadline slips due local DB setup | Keep the backend milestone to 9–12 focused hours, no worker/async DB/repository layer, protect Day 3 for AI, frontend, README, and demo. |
| OmniRoute compatibility assumed from account/key availability | No call here. Verify base URL, configured model, and structured-output behavior as an explicit AI-stage gate. |

## 11. Engineering review record

### Scope challenge and decision

- The request names nine backend areas and requires database-backed behavior plus failure tests. The current environment lacks the backend framework/ORM/migration/test packages, so a minimal dependency manifest and database setup are prerequisites, not optional polish.
- The current repository already has a single Deepgram smoke script; it does not provide an app/database pattern to reuse. No TODO tracker exists.
- D1 structure choice: user selected **B**, the compact separated-module arrangement above. Full milestone scope remains approved. No feature was cut or deferred from the nine requested items.
- Scope outcome: accepted as-is; arrangement compressed without removing scope. No remedy is awaiting user approval.

### Architecture review

- Boundary: FastAPI owns request validation; audio storage owns path/file rules; SQLAlchemy owns DB transactions; Alembic owns schema evolution. The route coordinates the file+DB operation and compensates on a handled DB failure.
- Data flow and all planned failure paths are in Section 5. Critical residual limitation is the non-atomic file/DB crash window, explicitly contained and deferred.
- No auth is approved for this single-user assignment MVP. Keep the server loopback-only; do not describe this as safe for public multi-user deployment.
- Distribution: local Python service and local PostgreSQL only. No CI/CD or publish path is added in this milestone. The test command and migration command are documented for future setup.
- Two shapes considered: (1) compact `sessions.py` owns the route contracts/validation and coordinates storage + request DB dependency, with storage policy hidden behind `audio_storage.py`; (2) add separate route, schema, service, repository, storage, and transaction modules. Shape 1 is selected because the workflow has one write route and two reads; additional pass-through layers would make a small app harder to trace. If retries/background processing or more write workflows arrive, split by new domain responsibility rather than prebuilding abstractions.

### Code quality review

- Use one settings source and one storage implementation; do not duplicate accepted file types across route and storage code. Derive OpenAPI from Pydantic request/response schemas.
- Keep user-supplied filename as sanitized display metadata; use generated storage keys only. API response models should make private fields impossible to serialize accidentally.
- Key edge cases are explicitly mapped in Section 5. Do not log request bodies, file bytes, full filenames, SQL exception text, DB URLs, API keys, or settings reprs.
- No existing app source callers/helpers qualify for extraction. The proposed test file can hold fixtures; split only when a second actual module reuses them.

### Test review

- Framework evidence: no test framework/configuration was found, and pytest is absent. This plan proposes pytest plus FastAPI TestClient; it does not install or execute it now.
- The test matrix covers success, real PostgreSQL persistence, boundaries, malformed upload, cleanup, history order/pagination, 404/422, migration parity, and secret/path non-disclosure. Storage unit tests use temporary directories; DB/API integration uses a dedicated PostgreSQL test DB.
- Do not accept SQLite-only tests as proof of PostgreSQL migrations or enum/check behavior. Run migration from an empty test DB and `alembic check`.
- No test source or test command ran during this planning session.

### Performance review

- Upload file bytes are copied in bounded chunks instead of loaded into one Python byte string. The cap and fixed history page size bound the MVP's storage/query work.
- Use a DB index supporting newest-first history, no N+1 joins because this milestone has only the session table, and short-lived sync sessions. FastAPI sync route handlers keep blocking SQL/disk work out of the event loop.
- No performance benchmark is justified for a single-user local assignment yet. Before public deployment, measure parser temp-disk behavior and establish request limits, DB pool sizing, and concurrent upload expectations.

### Outside voice

Outside voice unavailable: no external reviewer execution tool is exposed in this runtime. Search used official FastAPI, Pydantic, SQLAlchemy, and Alembic documentation; web research is not counted as an independent AI review. Missing cross-model coverage is disclosed.

### References

- FastAPI multipart uploads and `python-multipart`: [Request Forms and Files](https://fastapi.tiangolo.com/tutorial/request-forms-and-files/).
- FastAPI `TestClient`: [Testing](https://fastapi.tiangolo.com/tutorial/testing/).
- Pydantic environment settings and dotenv: [Settings Management](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/).
- SQLAlchemy session/transaction lifecycle: [Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).
- SQLAlchemy engine and PostgreSQL DBAPI URL: [Engine Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html).
- Alembic configuration and migration environment: [Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html); metadata comparison caveats: [Autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|---|---|---|---:|---|---|
| Eng Review | User invoked `$plan-eng-review` for the new backend milestone plan | Lock order, boundaries, error behavior, tests, and performance before implementation | 1 | ISSUES OPEN | Plan saved; implementation packages and PostgreSQL still unverified/absent; external review/log tooling limitations recorded below. |
| CEO Review | Not triggered | User asked for engineering plan, not product or scope expansion | 0 | Not run | — |
| Design Review | Not triggered | Backend-only work; no UI implementation planned | 0 | Not run | — |
| Adversarial | Not triggered | No implementation diff to audit | 0 | Not run | — |
| Outside Voice | Default plan-review step | Independent reviewer could not be dispatched with available runtime tools | 0 | Unavailable | No cross-model coverage; in-host review and official-doc research only. |

**VERDICT:** Plan is implementation-ready with B selected and scope retained. Do not begin provider integration in this milestone. No application code, tests, dependency installs, database changes, or Git setup were performed during this planning session.

Review log and readiness dashboard could not be recorded through gstack: the required state location is outside the project writable root. The plan and decision record are saved here as requested.

NO UNRESOLVED DECISIONS

## Implementation execution record — 2026-11-02

The user authorized implementation after providing the PostgreSQL settings. This record supersedes planning-only statements above where the two differ.

### Implemented source files

- `backend/requirements.txt` — minimal FastAPI, Uvicorn, SQLAlchemy, Alembic, psycopg, Pydantic Settings, multipart, HTTPX, pytest, and preserved Deepgram/environment dependencies.
- `backend/.env.example` — placeholder values only.
- `backend/app/__init__.py`, `config.py`, `database.py`, `models.py`, `audio_storage.py`, `sessions.py`, `main.py` — config, application, synchronous PostgreSQL setup, meeting session model, private audio store, and upload/history/detail routes.
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_create_meeting_sessions.py` — Alembic environment and initial schema migration.
- `backend/tests/test_sessions.py` — storage, settings, API, persistence, failure cleanup, history/detail, and migration tests using a dedicated PostgreSQL database guard.
- `backend/scripts/verify_database_connections.py` — safe connection status output only.

The requested session table has a UUID key, sanitized display filename, media type, size, duration, private storage key, exact five-state check constraint, UTC timestamps, positive-size/duration constraints, unique storage key, and history index. Audio writes are chunked, bounded, signature checked, generated-name only, temporary then atomically promoted, with handled-failure cleanup. API errors avoid returning SQL, local paths, or submitted values.

No frontend, provider integration, transcript/action models, Redis, WebSockets, authentication, or Git initialization was added. The existing Deepgram smoke script and sample WAV were preserved. `backend/.env` was not printed, copied, or modified.

### Verified runtime state

The existing root `.venv` is Python 3.12.6 and contains the declared backend stack. Dependencies were installed offline from the local wheelhouse. `pip check` passes. Test and development PostgreSQL database connections are verified. Detailed results and commands are recorded in the current verification record at the end of this plan.

## Earlier review and package installation investigation (historical)

The earlier network investigation documented a `WinError 10013` while contacting PyPI, and the static engineering review identified and fixed ambiguous commit-outcome cleanup. The user later supplied a local wheelhouse and confirmed offline installation into the existing `.venv`; the current runtime and migration verification is recorded below. Historical observations that packages were missing or checks had not run applied before this installation and are superseded by the current verification record.

### Optional offline installation reference

This procedure was used after the original network restriction; no longer a current blocker.

If this runtime cannot reach package indexes, use an authorized internet-connected Windows machine with Python 3.12 and transfer wheels through the approved channel:

```powershell
py -3.12 -m pip download --only-binary=:all: -r backend\requirements.txt -d wheelhouse
```

Then, from this project's `backend` directory, install to the existing venv without index access:

```powershell
..\.venv\Scripts\python.exe -m pip install --no-index --find-links <wheelhouse-path> -r requirements.txt
```

After installation, verify dependencies and execute Section 9. Do not install globally, create another venv, or bypass network/security controls.


## Runtime verification record - 2026-11-02 (historical snapshot; latest results follow)

The former package-index blocker is resolved for this environment: the user supplied an offline wheelhouse and dependencies were installed into the existing root `.venv` with `pip install --no-index --find-links ..\wheelhouse -r requirements.txt` from `backend/`. No internet installation or second virtual environment was used. `pip check` reports no broken requirements. `/wheelhouse/` was added to root `.gitignore`; wheelhouse contents were retained.

Configuration checks loaded settings from the backend configuration without displaying values and confirmed the development target is `ai_notetaker`, the test target is `ai_notetaker_test`, and the URLs are distinct. PostgreSQL connections succeeded. The test database was confirmed empty before migration; test DB was migrated first. Alembic upgrade from empty and repeat upgrade both succeeded, and `alembic check` reported no new operations. Schema inspection confirmed `alembic_version`, `meeting_sessions`, expected columns/constraints, and revision `0001_meeting_sessions`.

The first pytest run had two failures due to `UUID` missing from the test module imports. Added the missing test import; no assertions were weakened or removed in response to runtime failures. Rerun command from `backend/`: `..\.venv\Scripts\python.exe -m pytest -q` - **21 passed, 0 failed**, one Starlette TestClient deprecation warning (httpx compatibility notice). `pip check` also passed. The API verification used FastAPI TestClient configured explicitly against the test database and temporary private audio storage: app import, `/health` 200, OpenAPI paths, sample WAV upload 202/UPLOADED, history, detail, persisted DB row and stored-file presence all passed. Test data and temporary audio were cleaned up.

Only after test DB migration, pytest, and API verification succeeded, the development DB was inspected read-only. It was empty and had no Alembic revision; the planned initial migration was then applied. `alembic check` passed. Final read-only inspection showed both databases at `0001_meeting_sessions`, `meeting_sessions` present, zero rows in each. No destructive test operation was run against the development database.

Focused runtime defect fix: `backend/tests/test_sessions.py` now imports `UUID`, fixing the two NameErrors in test execution. Root `.gitignore` now ignores `/wheelhouse/`. No application code changes were needed in this verification turn. The earlier static review's ambiguous commit outcome handling remains covered by the passing regression tests.

Verification limits at the end of Day 1: the TestClient exercised API behavior without launching an external Uvicorn process; startup/import and OpenAPI were verified in-process. Day 2 later attempted the Deepgram application adapter and observed a network restriction; OmniRoute remains unconfigured, as detailed below. One deprecation warning remains from Starlette's use of `httpx` in TestClient; it did not fail tests. See `PROJECT_PROGRESS.md` for the concise milestone ledger.

Current next action: restore outbound TCP 443 from the Python runtime and verify live Deepgram transcription plus the full upload-to-completion path. OmniRoute is verified. After that gate and direct PDF requirement comparison, begin the narrow frontend milestone. The earlier standalone WAV smoke test is not application integration verification.


## Day 2 AI pipeline execution record - 2026-11-02 (historical snapshot; latest results follow)

This section supersedes the Day 1 plan's statements that transcription and AI analysis are out of scope. The earlier plan remains as a record of the approved Day 1 design and execution.

### Implemented

- `backend/app/providers.py`: Deepgram Listen v1 adapter using `nova-3`, `smart_format=true`, `diarize=true`, explicit stored MIME header and configured timeout; typed normalized transcript; OmniRoute HTTPX chat-completions adapter; strict Pydantic output models; at most one malformed-output repair request; safe provider failure categories.
- `backend/app/processing.py`: in-process `UPLOADED -> TRANSCRIBING -> ANALYZING -> COMPLETED` workflow; stage/error code on `FAILED`; transcript persisted before analysis; transcript replacement and topic/action replacement are transactional and ordinal-stable; failed analysis preserves transcript and retry resumes analysis where possible.
- `backend/app/models.py` and migration `backend/alembic/versions/0002_ai_results.py`: `transcript_segments`, `session_topics`, `action_items`, and `meeting_sessions.failed_stage` with foreign keys, cascade behavior and stable per-session ordinals.
- `backend/app/sessions.py` and `backend/app/main.py`: session detail returns transcript/topics/action items; task create/edit routes and failed-session retry route; upload schedules in-process processing.
- `backend/tests/test_ai_pipeline.py` and updates to `backend/tests/test_sessions.py`: mocked provider normalization, schema and repair tests, DB persistence, duplicate processing, transcript retention, retry, task operations, and complete mocked upload-to-results API flow. Tests never call real providers.
- `.env.example` contains placeholders for expected provider settings only; it has no real secret values.

### Root cause investigation: Deepgram connectivity

The app adapter is configured from centralized `Settings`; the effective Deepgram key is present without exposing its value. SDK source inspection confirmed the Listen v1 client sends to its managed API endpoint and accepts per-request headers; the adapter supplies the normalized audio MIME type. The sample WAV exists, the adapter timeout is 60 seconds, and the request uses the previously smoke-tested model/formatting plus diarization.

A real application adapter call failed with safe category `transcription_network_error` in 3.561 seconds. Independent sanitized probes showed DNS resolution succeeded, no proxy was configured, and outbound TCP connect to `api.deepgram.com:443` failed with Windows `PermissionError`/error 10013; an unauthenticated HTTPS probe failed at connect. No HTTP response was received, so this does not indicate authentication, provider quota, or payload rejection. No firewall, network control or key was changed. The prior standalone WAV smoke-test success remains a separate, earlier user-verified result. This environment needs outbound TCP 443 permission or the live app request must run from an authorized network.

### OmniRoute status

The centralized settings names are `OMNIROUTE_API_KEY`, `OMNIROUTE_BASE_URL`, and `OMNIROUTE_MODEL`. The effective settings returned all three as absent/empty. A real request was not attempted and no configured model name can be reported. Tests prove the adapter can construct the OpenAI-compatible `/chat/completions` request with JSON-object response mode and safely parse a mocked response; this is not live compatibility verification. Configure those fields locally without sharing the key value, then run a small real request.

### Final verification

- Historical test command result at that verification: `..\.venv\Scripts\python.exe -m pytest -q` - **46 passed, 0 failed**, one Starlette TestClient `httpx` deprecation warning. The latest run passed 48 tests as recorded below.
- `pip check`: **No broken requirements found**.
- Test database was migrated/checked before any development database operation; revision `0002_ai_results`, expected tables present, `alembic check` reports no new operations. The test suite and final read confirmed zero session rows afterward.
- Development database: existing revision `0002_ai_results`, expected tables present, zero session rows; no reset or destructive operation was performed. Its migration check reports no drift.
- FastAPI import succeeded; `/health` returned 200; OpenAPI contains upload/history/detail/action create/action patch/retry routes.
- Mocked API full flow: sample WAV upload -> `COMPLETED`; detail returned transcript, topic and task; history reflected completion; manual task create/edit worked. Retry and safe failure cases passed. This did not invoke real Deepgram or OmniRoute.
- Latest live Deepgram request failed with `transcription_network_error` before TLS/HTTP. OmniRoute is now live-verified with the approved local base URL/model; see the latest verification record below.
- Assignment PDF extraction tools/libraries are unavailable locally: `pdftotext`, `pdftoppm`, `mutool`, `qpdf`, `pdfinfo`, `pypdf`, `PyPDF2`, `pdfplumber`, `pdfminer`, `fitz`. No dependency was installed and no viewer was used. `IMPLEMENTATION_STRATEGY.md` retains the earlier assignment analysis, but no fresh comparison is claimed.
- `backend/.env` was not opened, copied, printed or modified. No Git, frontend, internet package installs, or development data deletion occurred.

**Day 2 status:** OmniRoute and its analysis persistence passed real application verification. Day 2 remains incomplete until Deepgram and the full live upload-to-completion flow pass.

**Next frontend milestone (after Day 2 gates):** build the narrow recorder/file upload page, REST upload, status polling, transcript/topic/action rendering, and task add/edit/complete controls. No frontend work began in this milestone.

## Latest integration and verification record - 2026-11-02

### Deepgram

Central settings loaded the key (presence only), `nova-3`, 60-second timeout, and sample WAV MIME `audio/wav`. The adapter initializes the installed Deepgram SDK Listen v1 prerecorded client with `smart_format=true`, `diarize=true`, and explicit content type. `samples/deepgram-test.wav` is available. The actual application request failed in 3.589 seconds with safe code `transcription_network_error`. DNS succeeded, but Python socket connection raised `PermissionError`/errno 13 before TLS; latest PowerShell `Test-NetConnection` also failed. No HTTP/authentication/provider response was received. A separate earlier user TCP probe succeeded, so runtime/network conditions differ or fluctuate. Real normalization and persistence from Deepgram output remain unverified.

### OmniRoute

Key presence was confirmed without displaying its value. The approved config is `http://localhost:20128/v1` and `kr/claude-sonnet-4.5`; defaults were added to `Settings` and `.env.example`, while process environment and `.env` continue to override them. The real response was fenced JSON; the model initially inferred a calendar date from a weekday. `parse_analysis` now unwraps only a fence spanning the complete response and retains strict Pydantic validation. Action assignees must occur in the transcript (or be `Unassigned`), due dates must be explicit dates found in the transcript, and timeframes must be explicitly present. Invalid output receives at most one repair, with the prior output included as untrusted data. A real request then passed strict schema/evidence validation. A real ANALYZING-stage test DB workflow reached `COMPLETED`; reload confirmed transcript, topic, and two action items persisted. The generated verification row was removed from the test database only.

### Verification results

- `..\.venv\Scripts\python.exe -m pytest -q`: **48 passed, 0 failed, 1 Starlette/httpx deprecation warning**.
- `..\.venv\Scripts\python.exe -m pip check`: no broken requirements.
- Test DB was upgraded first and `alembic check` was clean at `0002_ai_results`; all four expected tables were present. Development DB was checked read-only at the same revision with no schema drift. No development migration or data deletion occurred.
- TestClient runtime: health 200, OpenAPI 200, WAV upload 202, history/detail 200, action create 201, completion patch 200, retry 202, safe failure state. Existing tests cover mocked completion, provider errors, transcript preservation, duplicate processing, and one-repair behavior.
- Real full audio-to-analysis flow remains blocked at Deepgram. No real Deepgram transcript or real Deepgram-derived persistence is claimed.
- Assignment PDF was opened with Computer Use in Acrobat, but page text was not exposed via its accessibility tree. Screenshot capture showed an unrelated editor window, so automation stopped. Standard-library parsing found two pages but no extractable text; Word COM failed with Windows logon-session error and no local PDF/OCR utility is installed. PDF requirements comparison remains unverified.
- gstack skill-start initialized under Git Bash. `gstack-checks detect` failed because `bun` is unavailable; manual verification above completed. The gstack update-check subprocess also crashed; no setup/upgrade was attempted.
- Security incident: a screenshot result inadvertently showed VS Code with `backend/.env` open. No values are recorded here and `.env` was not modified. Rotate Deepgram/OmniRoute keys and the application DB role password; update local `.env` after rotation.

**Current next milestone:** after outbound Deepgram TCP 443 is restored and PDF requirements are confirmed, build the narrow React frontend for microphone/file capture, REST upload, status polling, transcript/topic/action display, and task add/edit/completion. Do not widen the approved architecture.
