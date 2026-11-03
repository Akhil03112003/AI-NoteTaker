# Assignment requirements checklist

Status recorded 2026-11-03. **Implemented** means present in source; **verified** means the stated check was actually run or explicitly user-confirmed.

## Backend

- [x] FastAPI REST workflow, PostgreSQL persistence/history, strict validated analysis output, Deepgram transcription, OmniRoute topic/action analysis, processing states, failure codes, retry, and task mutations are implemented.
- [x] User-confirmed real end-to-end run: upload returned HTTP 202; completed with 6 transcript segments, 2 topics, 4 action items; Deepgram, OmniRoute, and PostgreSQL persistence succeeded. This result was reported by the user, not re-run here.
- [x] Audio storage defaults to `%LOCALAPPDATA%\ai-notetaker\uploads`; focused config tests passed 2/2.
- [x] Storage config coverage: 2 focused tests passed; prior recorded full backend suite was 48 passed. No development database was changed.

## Frontend

- [x] React + TypeScript + Vite + Tailwind implementation; responsive dark workspace shell, navigation, meeting history, empty/loading/error states.
- [ ] shadcn/ui primitives are not integrated; current controls are native semantic elements with project CSS.
- [x] MediaRecorder Start/Pause/Resume/Stop, timer, permission/error handling, file upload for MP3/WAV/M4A/WEBM, client size/type checks, retry without discarding selected audio.
- [x] Typed REST client for implemented routes, status polling/backoff, retry, transcript and topic results, action-item add/edit/assignee/date/timeframe/priority/completion.
- [x] Dependencies installed by the user with `npm install` (157 packages, 158 audited); `frontend/package-lock.json` is present. User-reported install summary: 6 advisories (3 moderate, 1 high, 2 critical). Node 24.19.0 / npm 12.2.1. No `engines` or `packageManager` declaration.
- [x] Fixed missing `CircleHelp`, imported existing `ProcessingStatus`, corrected the `ApiError.name` test expectation, and separated Vite 6 build config from Vitest 2 test config to avoid mixing Vite 6 and Vitest's Vite 5 plugin types. No dependencies changed.
- [x] `npm run typecheck` passed. `npm run build` passed with Vite 6.4.5 (HTML 0.81 kB, CSS 34.82 kB, JS 201.95 kB). The required production build is verified.
- [ ] `npm run test` did not reach test collection: esbuild failed reading `../../../../..` with `Access is denied` while loading `vitest.config.ts`. The recorder regression and API client tests remain unverified.
- [x] Design-taste static lint: 0 FAIL, 2 WARN (zero-padding clock formats). Manual source review found and fixed recorder retry state handling and excessive screen-reader announcements; API contracts matched the backend source.
- [ ] Browser flows remain unverified. Playwright CLI open first failed `EPERM` creating its default `%LOCALAPPDATA%\ms-playwright\daemon`; redirecting CLI storage to workspace paths changed the failure to `Session closed` with an empty daemon error log. No screenshot/page was captured. The preview and backend responded to read-only HTTP checks (frontend 200, health 200, history 200, total 0); no upload, recording, action mutation, or database write was made.
- [ ] Run npm audit successfully. The attempted audit failed before returning findings because the npm advisory endpoint returned an error; the 6 advisory count above is only the user's `npm install` output.
- [ ] Run `src/hooks/useRecorder.test.tsx`; added to cover retry after a recorder error, but not executed.
- [ ] Verify valid file selection/actual upload, completed results, transcript/topics, action-item persistence, history reopen, failure/retry, responsive layout and browser console using Playwright when the CLI can launch a browser.

## Submission

- [ ] Re-read the assignment PDF and reconcile its exact requirements.
- [ ] Record a 2–3 minute walkthrough including success and an edge case.
- [ ] User handles Git repository/commit history. Do not initialize or operate Git during this work.
- [ ] Consider adding another sample recording if useful; `samples/deepgram-test.wav` exists.

## Commands

Run backend from `ai-notetaker\backend`:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run frontend in another terminal from `ai-notetaker\frontend` after dependencies are available:

```powershell
npm ci
npm run dev -- --host 127.0.0.1
```

Frontend checks:

```powershell
npm run typecheck
npm run test
npm run build
npm audit
playwright-cli open http://127.0.0.1:5173/
```

Frontend API base defaults to `http://127.0.0.1:8000`; override with `VITE_API_BASE_URL` in `frontend/.env.local` if needed. No provider credentials belong in frontend configuration.

`npm install` has already completed and the npm lockfile is available; use `npm ci` for a clean reproducible install. In this verification, typecheck/build passed, Vitest and Playwright were blocked by environment access errors, npm audit could not reach the advisory endpoint, and there is no `lint` script. Do not run a database migration for this verification.
