# AI Notetaker Project Context

**Last updated:** 2026-11-03  
**Purpose:** Continuity note for future Codex sessions. Read this file, `PROJECT_PROGRESS.md`, and the relevant planning document before continuing.

## Latest verified state (2026-11-03)

User-confirmed real application workflow: `POST /api/sessions` returned 202 and completed with 6 transcript segments, 2 topics, and 4 action items; Deepgram, OmniRoute, and PostgreSQL persistence succeeded. Earlier blocked-connectivity notes below are historical and superseded by this run. Audio defaults to `%LOCALAPPDATA%\ai-notetaker\uploads`. The Day 3 React/TypeScript frontend is implemented, but package installation is blocked by network/cache availability, so build, typecheck, frontend tests, and Playwright remain unverified. See [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md) and [ASSIGNMENT_REQUIREMENTS_CHECKLIST.md](ASSIGNMENT_REQUIREMENTS_CHECKLIST.md).

## Objective

Complete the three-day AI Notetaker technical assignment: record or upload a conversation, transcribe it, produce a topic summary and action items, and let the user revisit and edit saved results. The assignment PDF remains the source of truth at `C:\Users\akhil\OneDrive\Desktop\Project\_Embedded Audio & AI Systems Engineerssignment.pdf`.

## Project structure

```text
ai-notetaker/
├── .venv/                              # Existing Python 3.12.6 environment
├── backend/
│   ├── .env                            # Secret values never printed or documented
│   ├── .env.example                    # Placeholder values only
│   ├── requirements.txt                # Backend dependencies installed in existing root .venv
│   ├── alembic.ini
│   ├── alembic/env.py
│   ├── alembic/versions/0001_create_meeting_sessions.py, 0002_ai_results.py
│   ├── app/{__init__,main,config,database,models,audio_storage,sessions,providers,processing}.py
│   ├── scripts/{test_deepgram,verify_database_connections}.py
│   └── tests/{test_sessions,test_ai_pipeline}.py
├── docs/                                # Strategy, context, progress, backend plan
├── frontend/                            # React + TypeScript + Vite app; verification pending
├── samples/deepgram-test.wav            # Preserved smoke-test audio
└── .gitignore                           # Excludes env files and local uploads
```

No Git repository has been initialized; the user will handle Git separately.

## Approved stack and architecture

- Frontend: React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Lucide icons.
- Backend: Python, FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, Pydantic.
- ASR: Deepgram initial provider. The user has since verified the actual application flow through completion; prior connectivity failures are superseded. AssemblyAI is optional.
- LLM: OmniRoute is configured through centralized settings with the approved local base URL and model defaults. A real application request and PostgreSQL analysis-stage persistence succeeded after strict fenced-JSON normalization and transcript-evidence validation.
- Audio: browser MediaRecorder, then REST upload after Stop; audio stored privately under `%LOCALAPPDATA%\ai-notetaker\uploads` by default.
- Approach A, Complete Batch REST Application, is approved. Exact states: `UPLOADED`, `TRANSCRIBING`, `ANALYZING`, `COMPLETED`, `FAILED`.
- Authentication, collaboration, meeting integrations, realtime transcription, and WebSockets are outside the initial MVP.
- Validate structured LLM output locally with Pydantic. Provider keys stay server-side, never in frontend variables.
- Simple in-process background processing is acceptable for this assignment; it is not durable across server restarts.

## Configured services (no secrets)

- OmniRoute key presence was confirmed without displaying it. Base URL `http://localhost:20128/v1` and model `kr/claude-sonnet-4.5` are the approved configuration. A real application response passed strict Pydantic validation and analysis persistence.
- Deepgram key is reported saved in `backend/.env`; prerecorded WAV request succeeded per user in 3.279 seconds. No key value is recorded.
- `DATABASE_URL` and `TEST_DATABASE_URL` are reported configured in `backend/.env`. Both connections succeeded this session using PostgreSQL `psql` and `SELECT 1`; command output contained only status labels.
- User-provided DB names: development `ai_notetaker`, test `ai_notetaker_test`, role `ai_notetaker_app`.
- Existing root `.venv`: Python 3.12.6; FastAPI 0.162.0, SQLAlchemy 2.1.6, Alembic 1.20.1, psycopg 3.3.6, pytest 8.4.2, Uvicorn 0.54.0, pydantic-settings 2.16.2, python-multipart 0.0.33, HTTPX 0.28.1, Deepgram SDK 7.16.0, python-dotenv 1.2.4. Dependencies installed offline from the local wheelhouse; `pip check` passes.
- Docker CLI exists; daemon unavailable in the earlier check.

Never read out, print, or copy secret values. `backend/.env` remains unchanged and ignored by Git; `.env.example` contains blank secret placeholders and the approved nonsecret OmniRoute URL/model defaults.

## Current implementation state (historical snapshot; superseded by latest verified state above)

Backend implementation remains complete. The React + TypeScript frontend is now implemented; its build/typecheck/browser verification is pending because frontend dependencies could not be installed. The current user-confirmed real backend end-to-end result and frontend status are summarized at the top of this document.

Alembic revision `0002_ai_results` is applied to `ai_notetaker_test` and `ai_notetaker`. Both contain `meeting_sessions`, `transcript_segments`, `session_topics`, and `action_items`; test and development session counts were zero at the latest schema checks. Tests verify the mocked upload-to-results path and PostgreSQL persistence. The latest backend suite passed **48 tests, 0 failed**, with one Starlette TestClient deprecation warning.

At the earlier snapshot, the live Deepgram adapter request failed with `transcription_network_error`, OmniRoute settings were unconfigured, and the PDF had not been freshly inspected. The latest provider, network, test, PDF, and credential safety results are recorded in [Latest verification and handoff](#latest-verification-and-handoff---2026-11-02) below.

## Known risks

- Browser MediaRecorder MIME output and browser-to-server behavior have not been verified end to end.
- Deepgram success covers the earlier standalone WAV smoke test only; the application request is currently blocked by outbound socket denial. MP3/M4A/WebM are documented as supported formats, but were not individually tested with this account.
- OmniRoute live request and structured-output compatibility have been verified in an earlier application-level analysis run. It was not reached in the latest end-to-end upload because Deepgram failed first.
- Filesystem and DB commits are not atomic together; handled failures clean up files, while a process crash may leave an orphan.
- Multipart parsing may spool before handler-level size enforcement; this is a local assignment MVP.
- In-process processing is not durable across restarts; auth, collaboration, and realtime are deferred.
- Assignment wording about a “temporary sandbox key” still needs reconciliation with the provided provider credentials.

## Day 2 verification and provider diagnosis - 2026-11-02 (historical snapshot; see latest verification below)

- Latest application adapter call failed with safe category `transcription_network_error` in 3.561 seconds. Central settings reported Deepgram key configured; model is `nova-3`; timeout is 60 seconds. Adapter uses Deepgram SDK Listen v1 prerecorded API, `smart_format=true`, `diarize=true`, and explicit normalized media MIME.
- DNS lookup for `api.deepgram.com` resolved. TCP connect to port 443 raised `PermissionError` with Windows error 10013; unauthenticated HTTPS probe raised `ConnectError`. No proxy configuration was present. This is an environment/network permission blocker, not a timeout or an observed authentication/request rejection. No firewall/network setting was changed.
- Effective OmniRoute `Settings` had key, base URL, and model missing/empty. Settings supports `OMNIROUTE_API_KEY`, `OMNIROUTE_BASE_URL`, `OMNIROUTE_MODEL`; only mocked tests ran.
- See `PROJECT_PROGRESS.md` for migration/API/test results.

## Review and package-network diagnosis — 2026-11-02

- Static review covered backend app/config/database/model/storage/routes, Alembic setup/migration, test fixture safety, requirements, and `.env.example`. It found and fixed an ambiguous PostgreSQL commit outcome that could otherwise leave a session row pointing at deleted audio. The route now preserves audio unless a post-error read positively confirms the row. Runtime verification is complete; current results are recorded in `PROJECT_PROGRESS.md` and `BACKEND_IMPLEMENTATION_PLAN.md`.
- The test fixture guards exact DB names/role and performs cleanup only against `ai_notetaker_test`. It does not write test data to `ai_notetaker`. The test database was verified empty before its first migration.
- At the time of the earlier network investigation, the existing interpreter was the project `.venv` Python 3.12.6; pip was 26.2.2. pip config inspection found no settings or config files, and no proxy-related environment variables were set. WinHTTP reported direct/no proxy.
- A retry of `python -m pip install --retries 1 --timeout 8 -r backend/requirements.txt` failed with `WinError 10013` while connecting to `pypi.org:443`. Direct HTTPS probes to both PyPI and python.org also failed (`URLError`), so the failure is not pip-specific. PyPI's public status page reported operational service at the time.
- Windows Firewall reported all profiles enabled; that does not establish it caused the denial. Defender and registered antivirus status were unavailable to this process. No firewall, antivirus, or pip setting was changed.
- Safe offline option: on an authorized internet-connected Windows/Python 3.12 machine, download binary wheels with `py -3.12 -m pip download --only-binary=:all: -r backend/requirements.txt -d wheelhouse`; transfer the wheelhouse through the approved channel; install into this existing venv with `..\.venv\Scripts\python.exe -m pip install --no-index --find-links <wheelhouse-path> -r requirements.txt` from `backend`.

## Future-session workflow

Always read this file, `docs/PROJECT_PROGRESS.md`, and the relevant planning documents before continuing. Update relevant docs after each planning or implementation milestone. Never claim tests or provider integrations succeeded unless observed. Keep all planning and handoff information under `docs/`.

## Latest verification and handoff - 2026-11-02

This section supersedes earlier provider and test summaries while retaining their history.

- **Deepgram:** centralized settings confirmed key presence without displaying it; SDK invocation uses Listen v1, `nova-3`, `audio/wav`, `smart_format=true`, diarization, and a 60-second timeout. The real app adapter call failed with `transcription_network_error` after 3.589 seconds. DNS resolves, but Python socket connect raises `PermissionError`/errno 13 before TLS or HTTP, and the latest PowerShell TCP check also failed. A separate earlier user-run TCP probe succeeded; connectivity is intermittent or runtime/network-policy dependent. Authentication, HTTP request acceptance, response normalization, and DB persistence from real Deepgram output remain unverified.
- **OmniRoute:** settings resolve to the approved local endpoint/model; key presence was confirmed without value exposure. A real response used fenced JSON and initially inferred a calendar due date from a weekday. The adapter now unwraps only a complete Markdown fence, validates the inner JSON with strict Pydantic models, checks assignee/date/timeframe evidence against the transcript, and performs at most one repair attempt. A real request passed validation. A real ANALYZING-stage run against `ai_notetaker_test` reached `COMPLETED` and reloaded one transcript segment, one topic, and two action items; the generated test row was removed afterward.
- **Backend:** 48 pytest tests passed, zero failed, one Starlette/httpx deprecation warning; `pip check` reported no broken requirements. Test-first Alembic upgrade/check and development read-only check both report `0002_ai_results`, all four expected tables, and no schema drift.
- **API:** health 200, OpenAPI 200, WAV upload 202, history/detail 200, action create 201, completion patch 200, retry 202, and safe `FAILED` state were verified against the test DB. Existing tests cover provider failures, malformed output, retry, idempotency, and transcript preservation.
- **Assignment PDF:** Computer Use opened it in Acrobat, but the accessible page tree supplied no text and screenshot capture selected an unrelated editor window. Automation was stopped to avoid further display of the open environment editor. Standard-library PDF stream extraction found two pages but no extractable text; Word COM failed because the Windows logon session was unavailable, and local PDF/OCR utilities/libraries were unavailable. The PDF requirements have **not** been freshly compared.
- **Next step:** restore Deepgram outbound TCP 443 from the application runtime and rerun transcription plus the real upload-to-completion test. Then implement the narrow frontend: microphone/file capture, REST upload, polling, transcript/topics/actions, and task add/edit/completion.
- **Credential safety follow-up:** a desktop screenshot result unintentionally displayed VS Code with `backend/.env` open. No values were copied into project files or repeated in documentation, and `.env` was not modified. Rotate Deepgram and OmniRoute keys and the application DB role password, then update `backend/.env` locally; never send values in chat.

## Deepgram outbound connectivity investigation - 2026-11-02 (latest)

- **Project Python:** `C:\Users\akhil\OneDrive\Desktop\Project\ai-notetaker\.venv\Scripts\python.exe` (Python 3.12.6, Deepgram SDK 7.16.0). Its base interpreter is `C:\Users\akhil\AppData\Local\Programs\Python\Python312\python.exe`.
- **Observed failure:** the project Python resolves `api.deepgram.com` and `example.com`, but direct TCP connections fail with `PermissionError`, errno 13, Windows `winerror=10013`. The same failure occurs on ports 443 and 80. The base interpreter has the same TCP failure. HTTPX HTTPS probes fail at connect; TLS and HTTP are never reached. PowerShell `Test-NetConnection` and `curl.exe` also fail to connect to both Deepgram and an unrelated public host during this run. The user's earlier successful TCP probe remains a distinct earlier observation; the current failure is reproduced now.
- **Scope:** this is not specific to the Deepgram adapter, API key, request body, Python virtual environment, or Deepgram hostname. It is consistent with outbound remote-network traffic being denied in the current Windows execution context. Loopback checks to local OmniRoute and PostgreSQL succeeded.
- **Configuration checks:** no proxy-related environment variable names were present; Python reported no proxy, and WinHTTP was direct. DNS succeeds. No project source or `.env` changes were made.
- **Windows policy evidence:** Windows Firewall profiles are enabled and configured to allow outbound by default; local rule merging reports GPO-only. Three enabled outbound block rules were found, but none matched either Python executable or TCP port 443 in the inspected summaries. Firewall service is running. Detailed effective firewall and Defender/security-center CIM queries returned access denied or unavailable, so the enforcing product/rule cannot be identified from this user context. `TurboVPNService` is running, but its active connection/filter state was not established. Do not infer that it is the cause.
- **Conclusion and safe next action:** exact host enforcement is not proven. Repeat the transport probe in a normal, authorized PowerShell session outside the managed Codex command context. If it succeeds there but fails here, the managed execution context is the boundary; run the application-level Deepgram test from the authorized context. If it fails there too, ask the administrator to inspect effective outbound filtering/GPO and endpoint-security logs for the Python executable and remote TCP egress. Do not disable firewall or endpoint protection, and do not add broad allow rules.
- **Provider status:** no new Deepgram API request was made during this connectivity-only investigation; the application-level transcription remains unverified and blocked. The standalone earlier WAV smoke test and live OmniRoute verification remain as recorded above.

## Real workflow verification - 2026-11-03 (latest)

- The user confirmed a fresh standalone Deepgram WAV request succeeded from normal PowerShell, including TCP, TLS 1.3, and transcription, in 6.082 seconds. This verifies the standalone path only.
- The backend suite was rerun from the existing root `.venv`: **48 passed, 0 failed**, with one existing Starlette/httpx deprecation warning.
- A real FastAPI `TestClient` upload used `create_app` with its default `run_processing` processor and explicitly bound the SQLAlchemy session factory to `ai_notetaker_test`. Database names were checked in memory; the development DB was not used. `POST /api/sessions` returned 202 and created session `a27c2894-dd60-4c9c-8d3d-42c7e41d6c7c`.
- Processing ended in `FAILED` with safe code `transcription_network_error`. The session row persisted in the test DB, with zero transcript segments, topics, and action items. Consequently OmniRoute was not called for this session. This real application run did **not** reach `COMPLETED`.
- Follow-up API checks against the same test database returned `/health` 200, `/openapi.json` 200 (6 paths), and session history 200 (the failed upload is listed). The one failed test-database session was retained for inspection; no development data was touched.
- This differs from the user's normal-PowerShell standalone success and is consistent with the earlier managed command-context egress denial. Rerun the actual application upload from normal PowerShell using the test DB configuration to establish whether the app-level request succeeds there.

## Audio storage path diagnosis - 2026-11-03

- `Settings.audio_storage_dir` defaults to the relative path `uploads`. `Settings.resolved_audio_storage_dir` resolves relative paths against `BACKEND_DIR` (`backend/`), so the effective default is the absolute path `C:\Users\akhil\OneDrive\Desktop\Project\ai-notetaker\backend\uploads`, independent of whether the process starts from the project root or `backend/`.
- The target existed and was a directory. The existing root `.venv` Python process created, flushed, and deleted a temporary write probe there. `store_audio` accepted `samples/deepgram-test.wav` into that folder and the test object was removed afterward.
- The reported FastAPI 503 (`Audio storage is temporarily unavailable.`) was not reproduced by these direct storage checks. The upload route maps `StorageUnavailable` to that message; its lower-level I/O error is not logged by the route. Current evidence does not establish the exact cause of the other request. It may involve a different effective `AUDIO_STORAGE_DIR` or process security context; current-working-directory resolution alone is not the cause shown by this implementation.
- No application code, `.env`, secrets, or persistent audio files were modified. To confirm a process-specific difference, run the same storage probe in the same PowerShell process that constructs `TestClient`, then explicitly set `AUDIO_STORAGE_DIR` to the absolute backend uploads path for that process if needed.
