# AI Notetaker — Codex handoff

Status: 2026-11-03. The assignment PDF remains authoritative; its full direct re-check is still pending. This handoff reflects source inspection plus the user's latest real-run report.

## Objective and architecture

Record or upload a conversation, transcribe it, produce topic summaries and action items, and let users revisit and edit saved results. React 18 + TypeScript + Vite + Tailwind 4 + Lucide frontend; FastAPI + Pydantic + SQLAlchemy + PostgreSQL backend; Deepgram ASR and OmniRoute analysis. Audio is uploaded through REST after Stop; FastAPI background processing and session polling are used (no WebSockets).

## Backend status and verified functionality

Routes implement upload, history/detail, retry, task creation/editing, and health. The user subsequently verified a real application run from normal PowerShell: `POST /api/sessions` returned HTTP 202; final status `COMPLETED`; 6 transcript segments, 2 topics, 4 action items; Deepgram, OmniRoute, and PostgreSQL persistence succeeded. This run is user-confirmed and was not repeated during frontend development. Historical Day 2 notes below the latest progress summary that report provider network failure are superseded.

Today, audio storage defaults to `%LOCALAPPDATA%\ai-notetaker\uploads`; explicit environment-variable paths expand. Two focused configuration tests passed (one Starlette/httpx deprecation warning). Earlier backend suite: 48 passed, 0 failed, 1 warning.

## API contract (`backend/app/sessions.py`, response models in `backend/app/schemas.py`)

Errors: `{ "error": { "code": string, "message": string } }`.

| Method/path | Request | Response |
|---|---|---|
| `GET /health` | — | `{status:"ok"}` |
| `POST /api/sessions` | multipart `file`, optional form `title` | 202 `{id,title,status,created_at}` |
| `GET /api/sessions?limit=50&offset=0` | limit 1–100, offset ≥0 | `{items:[{id,title,status,created_at,file_size_bytes}],limit,offset,total}` |
| `GET /api/sessions/{session_id}` | UUID | Session metadata plus `safe_error_code`, `failed_stage`, `transcript_segments:[{id,ordinal,text,speaker_label,start_ms,end_ms}]`, `topics:[{id,ordinal,title,summary}]`, and `action_items:[{id,session_id,ordinal,description,assignee,due_date,timeframe,priority,is_completed}]` |
| `POST /api/sessions/{session_id}/action-items` | `{description,assignee?,due_date?,timeframe?,priority?}` | 201 action-item object |
| `PATCH /api/action-items/{action_item_id}` | Partial action-item fields, including `is_completed` | Updated action-item object |
| `POST /api/sessions/{session_id}/retry` | none | 202 `{id,status}`, failed sessions only |

Dates are ISO dates; IDs are UUID strings; optional values are nullable. Upload extensions: MP3/WAV/M4A/WEBM, capped at 25 MiB with MIME/signature checks. States: `UPLOADED`, `TRANSCRIBING`, `ANALYZING`, `COMPLETED`, `FAILED`. Analysis failure preserves transcript for retry. CORS defaults allow localhost and 127.0.0.1 on port 5173.

## Database and storage

- `meeting_sessions`: uploaded media metadata, state, timestamps, safe failure code/stage.
- `transcript_segments`: ordered text, optional speaker and millisecond bounds.
- `session_topics`: ordered title and summary.
- `action_items`: ordered task, assignee, optional due date/timeframe, High/Medium/Low priority and completion.
- Latest migration: `0002_ai_results`.
- Audio: private generated-name files in `%LOCALAPPDATA%\ai-notetaker\uploads` by default; `AUDIO_STORAGE_DIR` can override. Do not read or document `.env` values.

## Frontend status

Implemented: responsive dark workspace shell/history, recording controls and timer, microphone handling/cleanup, validated MP3/WAV/M4A/WEBM upload, typed REST client, exponential-backoff processing polling, retry, topic summaries, transcript with available speakers/timestamps, task add/edit/complete, history pagination/reopen, and empty/loading/error states. User installed packages successfully (157 added, 158 audited); `frontend/package-lock.json` is present. Node 24.19.0 / npm 12.2.1. Four reported TypeScript errors were fixed: missing Lucide/type imports and the test's `ApiError.name` shape; Vite config was split between Vite 6 build plugins and Vitest 2 test options to avoid incompatible Vite 6/Vite 5 plugin types. No dependency versions changed. `npm run typecheck` and `npm run build` pass. `npm run test` cannot load `vitest.config.ts` because esbuild receives `Access is denied` while traversing `../../../../..`; no tests collected. `npm audit` could not reach the npm advisory endpoint; user-reported install output listed 6 advisories (3 moderate, 1 high, 2 critical). Preview returned HTTP 200; dev server starts but Vite dependency optimization fails with a similar parent-directory permission issue. Playwright CLI was invoked; default daemon directory creation failed with EPERM, and workspace-redirection retries ended `Session closed` with an empty daemon error log. No browser page or screenshot was captured, so browser workflows are unverified. Manual review found no frontend provider keys or unsafe HTML insertion and confirmed the API client route/schema names against backend source. shadcn/ui primitives remain unintegrated.

## Constraints and decisions

- Never read/expose `backend/.env`; do not change credentials or database contents; no Git operations.
- No WebSockets, Redis/Celery, authentication, or collaboration features. REST upload after Stop is intentional.
- Use backend schemas as API authority. Do not fabricate speaker names, times, owners, or due dates.
- Visual direction: restrained near-black workspace with lime accents; no fake metrics.
- Installed `impeccable` skill launcher could not run because its engine was absent and the external install location is not writable. Use its already-read local references as manual guidance. Frontend browser and skill lint/inspect remain pending with dependency availability.

## Exact commands

Backend, from `ai-notetaker` root:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend, second terminal from root:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open the Vite URL, normally `http://127.0.0.1:5173`. Last verification: typecheck and build passed; Vitest config startup, Playwright browser launch, and npm audit are blocked as described above. No frontend lint script is declared. Git-based `$verify` detect/status and `$review` diff review were not run because Git operations are prohibited. Manual source review was done instead. The backend was started and health/history GETs succeeded without migration or writes. Earlier backend focused storage tests passed: `..\.venv\Scripts\python.exe -m pytest -q tests/test_sessions.py::test_relative_storage_path_is_independent_of_working_directory tests/test_sessions.py::test_storage_path_expands_local_app_data_setting` (2 passed).

## Remaining assignment work

Resolve the local Vitest/Playwright access blockers; complete frontend tests, audit and browser workflows; re-read the assignment PDF; record the required 2–3 minute demo; user handles GitHub repository/commit history. Track details in `docs/ASSIGNMENT_REQUIREMENTS_CHECKLIST.md`.
