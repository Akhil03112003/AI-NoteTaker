# AI Notetaker

Record or upload a meeting, then review its transcript, topic-organized notes, and editable action items. See [project context](docs/PROJECT_CONTEXT.md), [progress](docs/PROJECT_PROGRESS.md), and the [assignment checklist](docs/ASSIGNMENT_REQUIREMENTS_CHECKLIST.md) for implementation and verification status.

## Architecture

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS 4, Lucide icons. Browser recording is uploaded over REST after Stop.
- **Backend:** FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic. Deepgram transcribes audio; OmniRoute generates validated topic summaries and action items. Processing runs as an in-process background task.
- **Storage:** Private local audio files at `%LOCALAPPDATA%\ai-notetaker\uploads` by default. Database and provider settings stay on the backend.

REST-after-Stop keeps the first version simple and avoids a streaming socket service. A recording must finish uploading before backend processing begins; status is read by polling the session endpoint.

## Run locally (PowerShell)

Ensure PostgreSQL and provider configuration are available to the backend. Keep `backend/.env` private. From the project root:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open the Vite URL printed by the dev server (normally `http://localhost:5173`). The frontend API base defaults to `http://127.0.0.1:8000`; set `VITE_API_BASE_URL` in `frontend/.env.local` only when the backend uses another address. Do not put provider keys in frontend variables.

Dependencies were installed successfully and `frontend/package-lock.json` is present. Use `npm ci` for repeatable installs. For an existing database, the command above starts FastAPI without running migrations; initialize a new database separately using the project's migration instructions.

## Verify

From `frontend`:

```powershell
npm run typecheck
npm run test
npm run build
```

From `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Current recorded results and outstanding browser verification are in `docs/PROJECT_PROGRESS.md`. Latest frontend verification: `npm run typecheck` and `npm run build` passed; Vitest failed before test collection due restricted parent-directory access; Playwright CLI failed to keep its browser daemon alive after redirecting its profile/cache path; `npm audit` could not reach the advisory endpoint. User-reported install output listed 6 advisories (3 moderate, 1 high, 2 critical). No lint script is declared. The latest successful real backend end-to-end run was user-confirmed: upload accepted with HTTP 202 and completed with 6 transcript segments, 2 topics, and 4 action items.
