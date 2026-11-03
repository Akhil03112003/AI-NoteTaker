# AI Notetaker Implementation Strategy

**Status:** Approved for planning, Approach A: Complete Batch REST Application  
**Last updated:** 2026-11-03  
**Implementation status:** Backend and frontend feature work are implemented. User-confirmed real app run completed with Deepgram + OmniRoute and persisted 6 transcript segments, 2 topics, and 4 action items. Frontend build/typecheck/browser verification remains pending because dependencies are not locally available and network installation failed. Audio default: `%LOCALAPPDATA%\ai-notetaker\uploads`.

This plan is based on the assignment PDF at `C:\Users\akhil\OneDrive\Desktop\Project\_Embedded Audio & AI Systems Engineerssignment.pdf` and the user's approved decisions. The assignment is the source of truth for evaluation requirements. The user has approved Approach A and the batch REST transport.

## 1. Assignment requirements

### Functional requirements

| Area | Mandatory requirement |
| --- | --- |
| Audio capture | Browser interface with Start, Pause/Resume, and Stop controls. |
| Audio upload | Fallback upload for `.mp3`, `.wav`, `.m4a`, and `.webm`. |
| Capture/processing feedback | Clear states such as Recording, Uploading, Processing, and Completed, plus an active visualizer or a recording timer. |
| Transcription | Automated speech-to-text service. The assignment gives OpenAI Whisper, Deepgram, AssemblyAI, and local Whisper as examples. |
| Executive summary | Concise overview structured by key discussion topics. |
| Action items | Discrete tasks with description, assignee (inferred or `Unassigned`), due date/timeframe when explicitly mentioned, and inferred High/Medium/Low priority. |
| Structured LLM output | Strict JSON or schema validation to reject malformed output. |
| Results view | Side-by-side or tabbed transcript and AI insights. Transcript may be raw or segmented, with speaker labels/timestamps where available. Insights include the formatted summary and interactive task checklist. |
| Task state | Toggle completion, edit task text, and manually add tasks. |
| Persistence/history | Save processed sessions and allow them to be revisited in a history list. |

The assignment labels the final capability â€œExport / Persistence,â€ but its explanatory requirement specifically says to persist sessions and revisit them through history. It does not specify a separate download format. Do not add a standalone export format unless the evaluator clarifies that it is expected.

### Technical requirements and freedom

- Assignment framework choices: Next.js, React, or SvelteKit; Node.js, Python, or Go on the backend.
- Keep a clean frontend component architecture and predictable state management.
- Provide a clear `.env.example` configuration.
- The assignment says, â€œPlease issue a temporary sandbox key.â€ It does not identify the service or clarify who issues it. The user now reports that the OmniRoute account/API key and Deepgram key are available. Keep those values private and document only service/configuration status.
- Choose WebSocket streaming or browser recording followed by REST upload after Stop, and explain the trade-off in the README. The approved choice is REST after Stop.

### Evaluation criteria

| Criterion | Evaluator looks for |
| --- | --- |
| System architecture | Clear separation between client capture, server processing, and third-party AI APIs. |
| Resilience/error handling | Graceful microphone permission denial, failed network requests, rate limits, encoding issues, and malformed LLM outputs. |
| Prompt engineering | High-quality, deterministic summary/task prompts without truncation or formatting drift. |
| Code quality/typing | Clean readable code, strict typing such as TypeScript/Pydantic/static types, and sensible folder hierarchy. |
| Frontend UX/polish | Thoughtful latency and async loading behavior, including spinners/skeletons and progress feedback during transcription/analysis. |

The PDF specifies no numeric scores, weights, or minimum transcription-accuracy threshold.

### Submission deliverables

1. GitHub repository, public or invited-private, containing source and commit history.
2. README with setup/local execution, architecture and trade-offs, limitations, and future work.
3. One or two short `.mp3` or `.wav` samples in `/samples`.
4. A 2â€“3 minute Loom video or short walkthrough covering the happy path and edge-case handling.

Git initialization is intentionally deferred because the user wants to handle Git separately. This does not remove the GitHub repository/commit-history submission requirement; it remains pending until the user handles Git.

## 2. Product definition and MVP

### Problem

After a spoken discussion, a user has to reconstruct what was said, identify decisions and tasks, and remember owners and timing. The application turns a recording into a transcript and editable meeting notes, then preserves them for later review.

### Primary user workflow

1. Start a microphone recording or upload an existing audio file.
2. Pause/resume or stop; show the recording timer and clear capture/upload/processing state.
3. After Stop, upload the audio through REST and process it on the backend.
4. Review the transcript, topic-organized summary, and structured action items.
5. Edit/check tasks or add a task manually.
6. Reopen a saved session from history.

### Essential UI

- Recording/upload page with Start, Pause, Resume, Stop, timer, upload control, and clear errors.
- Results page with a transcript view and an insights view (tabs or split layout).
- Action item checklist with edit/add/completion controls.
- History list with session title/date/status.
- Visible asynchronous states. Show stage-level progress; use indeterminate progress unless a provider exposes trustworthy percentage progress.

### MVP exclusions

- Real-time transcription and WebSockets.
- Authentication, collaboration, multi-user tenancy, and meeting integrations/bots.
- Calendar, CRM, task tracker, or notification integrations.
- Chat over prior meetings, advanced search/analytics, and standalone PDF/CSV export unless clarified by the evaluator.
- A second required ASR integration. Deepgram is the initial provider and its prerecorded WAV smoke test succeeded; AssemblyAI is optional, not a requirement.
- Speaker diarization when the selected service does not provide it. Preserve/display speaker labels and timestamps when returned; do not invent them.
- An independent audio visualizer. A recording timer satisfies the assignment.

## 3. Approved architecture: Approach A

### Approved technology stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Lucide icons.
- **Backend:** Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pydantic.
- **ASR:** Deepgram is the initial provider. The earlier standalone WAV smoke test succeeded in 3.279 seconds per user verification. The app adapter is implemented, but its latest live request failed with `transcription_network_error`; DNS resolved and outbound TCP 443 was denied by Windows error 10013. Deepgram documents MP3, WAV, M4A and WebM support ([supported audio formats](https://developers.deepgram.com/docs/supported-audio-formats)); the local account/network has not individually verified those formats.
- **LLM:** OmniRoute adapter is implemented. No live request has been made because effective Settings returned no API key, base URL, or model; mocked response and validation paths pass.
- **Audio:** Browser MediaRecorder; send the finished recording by REST after Stop. File upload uses the same backend path.

### Frontend architecture

Organize the UI by user flow: recorder/upload, session history, result/transcript, insights/action items, and typed API client. Keep API state and request lifecycle predictable. The browser owns capture controls and recording timer; the backend owns processing state and persisted results. Do not put provider credentials in frontend configuration.

Expected UI states include idle, recording, paused, uploading, `UPLOADED`, `TRANSCRIBING`, `ANALYZING`, `COMPLETED`, and `FAILED`. Explain microphone denial and preserve the file-upload alternative.

### Backend architecture

Separate FastAPI routes, request/response schemas, SQLAlchemy persistence, processing orchestration, Deepgram client, and OmniRoute client. The API accepts a recording, stores it, creates a session, and returns its ID. A simple FastAPI background task runs the batch pipeline through transcription, transcript persistence, topic/action analysis, and completion/failure; the frontend polls session status. The mocked database-backed flow is verified, while live providers remain blocked as recorded in `PROJECT_PROGRESS.md`. This is intentionally small for a three-day assignment. An in-process task is not durable across a server restart, so expose failure and retry behavior rather than promising durable queuing.

### PostgreSQL model

| Table | Suggested fields |
| --- | --- |
| `meeting_sessions` | UUID primary key, title, original filename, media type, byte size, duration, private audio storage key, status enum, failed stage/safe error code, created/updated/completed timestamps. |
| `transcript_segments` | UUID, session foreign key, ordinal, text, nullable speaker label, nullable start/end time in milliseconds. |
| `session_topics` | UUID, session foreign key, ordinal, topic title, concise topic summary. |
| `action_items` | UUID, session foreign key, description, assignee, nullable explicit due date, nullable timeframe text, priority enum, completion boolean, ordinal, timestamps. |

Use foreign keys and cascade child rows when removing a session. Store tasks as rows so edits and completion persist independently. Use nullable date/timeframe values when no due information was explicitly stated. Store `Unassigned` when no assignee can be inferred. Apply Alembic migrations from the start.

### Processing states

Persist exactly these domain states (uppercase):

`UPLOADED â†’ TRANSCRIBING â†’ ANALYZING â†’ COMPLETED`

Any failed stage transitions the session to `FAILED`, with a safe stage/error code and a user-facing retry path. `UPLOADED` means backend intake succeeded; `TRANSCRIBING` and `ANALYZING` indicate the active stage.

### REST API contract

The following routes are the planning contract; response field names can be finalized with the Pydantic schemas before implementation.

| Method/route | Purpose | Expected result |
| --- | --- | --- |
| `POST /api/sessions` | Multipart upload from MediaRecorder or file picker. | `202 Accepted`, session ID and `UPLOADED` status. |
| `GET /api/sessions` | History list. | Session ID, title, creation date, status. |
| `GET /api/sessions/{session_id}` | Poll processing or load a saved result. | Status, segments, topics, action items, and safe error details. |
| `PATCH /api/action-items/{action_item_id}` | Edit description/assignee/date/timeframe/priority or completion. | Updated task. |
| `POST /api/sessions/{session_id}/action-items` | Manually add a task. | Created task. |
| `POST /api/sessions/{session_id}/retry` | Retry a failed stage when the stored audio remains available. | Session moves back to the appropriate processing status. |

Use consistent error responses. The UI should distinguish invalid/unsupported audio, upload failure, provider rate limiting/outage, invalid credentials, and invalid LLM output. Disable duplicate submit while uploading and retain the local recording Blob long enough to retry a failed upload.

### Audio storage

Store audio as a file outside public/static assets under a configurable local persistent directory. Use generated IDs for stored names; do not trust client filenames as storage paths. Do not store audio bytes in PostgreSQL. Retaining local audio supports processing retry and the assignment demo. Choose upload size/duration limits from the selected provider and actual browser output; the assignment does not state numeric limits. The provider must be checked against all four required upload formats and the MediaRecorder MIME type. Add conversion only if needed.

### Audio/AI pipeline

1. Browser MediaRecorder captures microphone audio locally and provides Start/Pause/Resume/Stop controls. A file picker provides the fallback formats.
2. On Stop, POST the Blob as multipart REST data. File uploads use the same route.
3. FastAPI validates allowed format, size, and decodability; creates a `meeting_sessions` row with `UPLOADED`; stores the file privately.
4. Processing advances to `TRANSCRIBING`; the Deepgram client sends the audio and receives text/segments and any available speaker/time metadata.
5. Persist transcript segments. Advance to `ANALYZING`.
6. Send transcript text to OmniRoute (not the audio) for topic-based summary and action extraction.
7. Validate output with Pydantic, persist topics/tasks, and mark `COMPLETED`; otherwise mark `FAILED` at the stage that failed.
8. Frontend polls the session endpoint and renders the completed result or retryable error.

The current adapter sends the full persisted transcript without local truncation. The effective OmniRoute model is not configured, so its context window cannot be checked yet. If the configured model rejects a long transcript, surface an analysis failure and preserve the transcript; implement segment-boundary chunking only if the real model limit requires it.

### OmniRoute and structured output

Keep the OmniRoute base URL, API key, and model selection in the backend environment. Verify the configured model and structured-output behavior with a small request before depending on schema enforcement. A gateway's OpenAI-compatible shape does not guarantee identical feature support for every provider/model. Use schema-constrained JSON where supported, but always validate locally with Pydantic (`extra=forbid`, required fields, priority enum, bounded strings). If malformed, make at most one controlled repair attempt; after that, preserve the transcript and expose analysis failure/retry.

Prompt rules: use only transcript evidence; do not fabricate owners or deadlines; use `Unassigned` where unclear; only populate date/timeframe when explicitly mentioned; priority must be High/Medium/Low; group summary by discussion topics. Test output against scripted sample audio and reference text.

### Frontend/backend communication

Use REST for upload and mutations. Poll `GET /api/sessions/{id}` at a modest interval with backoff while processing. WebSocket updates and streaming partial transcripts are out of scope. Show stage-level progress and elapsed time, not a fabricated percentage. Keep audio/LLM/ASR keys out of browser requests and frontend environment variables.

## 4. Engineering decisions

| Concern | Decision |
| --- | --- |
| REST vs WebSockets | REST after Stop is approved. The PDF permits it; live capture does not require a live transcript. It avoids connection lifecycle/reconnect complexity. Document the trade-off in README. |
| Audio persistence | Private local file storage, separate from PostgreSQL. Retain for retry/demo; choose a size policy after verifying Deepgram limits. |
| Database | Relational session, transcript segment, topic, and action-item tables; Alembic-managed schema. |
| Output validation | Pydantic validation remains authoritative even if OmniRoute/model accepts a JSON schema. One repair attempt, then visible failure with transcript preserved. |
| Provider retries | Bounded backoff for transient 429/5xx, honoring `Retry-After`; do not retry bad keys or unsupported formats. Avoid retry loops that duplicate provider usage. |
| Frontend/API retries | Show errors and preserve local audio for re-upload after network failure; disable duplicate submissions. Poll session status instead of using sockets. |
| Secrets | Real keys stay in `backend/.env`, ignored by Git. Provide `backend/.env.example` with names/placeholders only. Never use `VITE_` for provider secrets. Never log key values or audio/transcript contents. |
| Git | Do not initialize Git until the user handles it. A root `.gitignore` is added in this documentation update so `backend/.env` and other env files are excluded when Git is later initialized. |
| AssemblyAI | Optional comparison/fallback only. No requirement to build an AssemblyAI integration. |

Suggested configuration names (placeholders only): `DATABASE_URL`, `OMNIROUTE_BASE_URL`, `OMNIROUTE_API_KEY`, `OMNIROUTE_MODEL`, `DEEPGRAM_API_KEY`, `AUDIO_STORAGE_DIR`, `MAX_UPLOAD_MB`, `CORS_ORIGINS`. Do not put values in this document.

## 5. Three-day implementation plan

The plan is ordered to validate external service behavior and audio format compatibility before the pipeline depends on them. No milestone below is marked complete until actually verified.

### Day 1 â€” Verify Deepgram and create the upload/session vertical slice

1. Prepare a short scripted WAV sample with known reference text; plan a second clip with names, multiple speakers, or explicit owners/dates if time permits. The repository currently has no sample clips.
2. Run a Deepgram authentication/transcription smoke test using the key already in `backend/.env`. Do not print the key. **Verified:** `samples/deepgram-test.wav` transcribed successfully in 3.279 seconds; transcription returned correctly (user-verified).
3. Check the browser's actual MediaRecorder MIME type and test required file formats. Decide whether conversion is necessary only after observing provider behavior.
4. Implement backend settings/schema, Alembic session/transcript/task migrations, upload validation/storage, `POST /api/sessions`, and session status retrieval.
5. Implement the browser recorder/upload controls and state display; use REST on Stop.

**Dependencies:** a short test audio file, working local database, and safe loading of the Deepgram key. Git remains under user control and is not initialized by this plan.

**Verification milestone:** Deepgram prerecorded WAV smoke test succeeded (user-verified); upload/session persistence, unsupported formats/permission denial, and browser state transitions remain pending.

**Day 1 deliverable:** verified Deepgram request contract (or documented blocker), persisted upload/session vertical slice, and recording/upload interface.

### Day 2 â€” Complete transcription, OmniRoute analysis, and dashboard persistence

1. Implement Deepgram transcription client and persist transcript segments, timestamps, and speaker labels when returned.
2. Implement OmniRoute summary/action prompt and strict Pydantic schema validation. Verify one real model call without exposing key values.
3. Persist topic summaries and action items; add bounded provider retries and failure-stage handling.
4. Build history, transcript/insights view, and task edit/add/completion operations.
5. Add backend unit/API tests using provider fakes, plus database-backed persistence checks.

**Dependencies:** Day 1 upload model, provider response contract, and access to the configured OmniRoute service.

**Verification milestone:** a sample recording reaches `COMPLETED`; database reload restores transcript, topics, and tasks; task changes persist; malformed LLM output is rejected and session remains recoverable.

**Day 2 deliverable:** the complete happy path and editable session history.

### Day 3 â€” Resilience, documentation, and submission demo

1. Exercise microphone denial, network failure, unsupported/corrupt audio, size limits, Deepgram rate limits/outage/invalid key, OmniRoute failure, and malformed structured output.
2. Fix required-path issues; retain partial session/transcript data when later processing fails and expose retry affordances.
3. Run backend tests, frontend type/lint checks, and Playwright CLI end-to-end flows. These are planned checks and have not been run.
4. Complete README setup, local execution, architecture, REST-vs-WebSocket rationale, limitations, and next steps.
5. Add 1â€“2 short `.mp3` or `.wav` samples under `/samples`; ensure they are safe to share.
6. Record a 2â€“3 minute happy-path plus edge-case walkthrough.
7. After the user handles Git, confirm source/history and that secrets are not committed. Do not initialize Git as part of this plan.

**Dependencies:** Day 2 pipeline and session dashboard; user-owned Git setup remains outstanding for final repository delivery.

**Day 3 deliverable:** tested application, README, sample clips, demo, and GitHub submission once user-managed Git/repository work is completed.

### Remaining testing milestones

- **Backend unit/API:** provider normalization, settings aliases, strict schema/repair behavior, failure transitions, retry, transcript preservation, task operations, and duplicate processing are covered by the latest 46-test PostgreSQL-backed run; live provider calls remain blocked/unconfigured.
- **Backend API/database:** mocked upload-to-results, history/detail, task create/edit/check, retry, and persistence after reload passed. A real-provider end-to-end session remains pending.
- **Provider checks:** earlier standalone Deepgram WAV smoke test succeeded per user verification. The latest application request failed before HTTP due to outbound TCP denial. OmniRoute live request is pending its three effective settings. MP3/WAV/M4A/WebM provider account tests and browser MediaRecorder output remain pending. AssemblyAI is optional.
- **Frontend/browser:** Start/Pause/Resume/Stop, timer/state transitions, denied mic permission, file fallback, processing status, history navigation, task edits.
- **End-to-end:** complete sample upload to results and a forced error/recovery case. Use Playwright CLI after the happy path is implemented.
- **Submission checks:** README setup from a clean environment, sample file extension/location, demo length/content, no secret exposure.

## 6. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Deepgram credit/account availability or limitations change | Initial prerecorded WAV request succeeded in 3.279 seconds. Verify other input formats, browser MediaRecorder output, quota/rate-limit, and failure behavior without recording the key. Keep the ASR client boundary small. AssemblyAI stays an optional alternative; local Whisper is a contingency only if the initial provider cannot be used. |
| OmniRoute/model structured-output behavior differs | Make one small real request against the configured model early; validate with Pydantic regardless of provider-side schema support. |
| Audio size/format incompatibility | Verify MP3/WAV/M4A/WebM and the browser's actual recording MIME type; set configurable limits after checking Deepgram. Convert only if a real incompatibility requires it. |
| LLM hallucinated or malformed action fields | Ground the prompt in transcript evidence, require explicit dates, default unclear assignee to `Unassigned`, validate enum/schema, allow one repair call, preserve transcript on failure. |
| Three-day time limit | Avoid WebSockets, Redis/queue, auth, and integrations. Build a persisted vertical slice first, then result editing, then resilience/docs/demo. |
| In-process background task lost on backend restart | Mark interrupted work failed or retryable; retain audio and status. Durable queue is explicitly deferred beyond this MVP. |
| Secret accidentally added after Git setup | Root `.gitignore` excludes env files. Check status/diff before any later commit; keep secrets server-only and out of docs/logs. |

## 7. Final recommendation and current status

Proceed with approved Approach A: one complete batch REST workflow, Deepgram as the initial ASR provider, and OmniRoute for transcript analysis. The initial Deepgram request configuration is verified: Listen v1 prerecorded file transcription using `deepgram-sdk` 7.16.0, model `nova-3`, and `smart_format=true`; the test WAV succeeded in 3.279 seconds. This only verifies the tested WAV request, not all formats or browser audio. Prioritize one persisted end-to-end path, visible failures/retry, typed schema validation, and submission materials. Do not expand to real-time transcription, WebSockets, authentication, collaboration, or meeting integrations in the initial MVP.

**Current next action:** install frontend dependencies when package registry access is available, then run TypeScript, Vitest, production build, and Playwright checks. The user has confirmed a real backend upload through `COMPLETED` with Deepgram, OmniRoute, and PostgreSQL persistence. Do not repeat the older connectivity blocker as current status; see [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md).



## Day 2 backend execution record - 2026-11-02 (historical snapshot; see latest verification below)

The Day 2 adapter, persistence, API, and mocked verification work is recorded here; the original assignment requirements and architecture remain unchanged.

- Deepgram adapter uses the installed SDK's prerecorded Listen v1 endpoint with model `nova-3`, `smart_format=true`, diarization, the configured timeout, and the stored normalized MIME type. Normalization groups provider words by speaker and converts seconds to milliseconds. When word reconstruction differs from the complete provider transcript, the code falls back to one full un-attributed segment to avoid silent text loss.
- Latest actual application adapter request using the sample WAV failed with `transcription_network_error` after 3.561 seconds. Safe diagnostics resolved `api.deepgram.com` DNS but direct TCP 443 raised `PermissionError`/Windows error 10013; proxy was not configured. The prior standalone WAV smoke test remains separately user-verified. This was not an authentication or provider response result; no code change can remove the external socket restriction.
- OmniRoute settings use the expected names `OMNIROUTE_API_KEY`, `OMNIROUTE_BASE_URL`, and `OMNIROUTE_MODEL`; all were empty/missing in effective centralized Settings. No real request was attempted. Mocked tests cover OpenAI-compatible JSON-object response parsing, safe HTTP error categories, schema rejection, one repair attempt, and settings/env precedence.
- Alembic `0002_ai_results` adds `failed_stage`, `transcript_segments`, `session_topics`, and `action_items`. Both databases verified at that revision; test-first Alembic check reported no drift. The application preserves transcripts across analysis failure and retries only the failed stage.
- At that earlier verification: **46 passed, 0 failed, 1 Starlette TestClient deprecation warning**. This historical run covered the mocked PostgreSQL upload-to-results flow and provider cases; the latest suite has 48 passing tests as recorded below.
- PDF re-extraction was attempted using local command and Python library availability checks. `pdftotext`, `pdftoppm`, `mutool`, `qpdf`, `pdfinfo`, `pypdf`, `PyPDF2`, `pdfplumber`, `pdfminer`, and `fitz` were not available; no install/viewer was used. The existing assignment analysis remains the recorded source summary, but no fresh PDF comparison is claimed.

**Day 2 completion:** not complete. Waiting on reachable Deepgram TCP 443 and the three locally configured OmniRoute fields, followed by live provider and end-to-end verification. No frontend implementation was started.

## Latest provider and assignment verification - 2026-11-02

This record supersedes older status statements while preserving them as history.

- Deepgram is **not application-verified**. The key loads; the adapter uses `nova-3`, WAV MIME, smart formatting, diarization, and a 60-second timeout. The actual call failed with `transcription_network_error` in 3.589 seconds. DNS resolved; TCP connect from the Python runtime failed with `PermissionError`/errno 13 before TLS/HTTP. The latest PowerShell TCP probe also failed, although the user previously measured TCP success separately. Authentication, model acceptance, real response normalization, and transcript persistence remain unknown.
- OmniRoute is **application-verified** at `http://localhost:20128/v1`, model `kr/claude-sonnet-4.5`, using key-presence-only checks. The real response was fenced JSON and initially inferred a calendar date from ?by Friday?. The parser strips only a whole-response JSON fence before strict Pydantic validation; evidence checks reject invented owners, dates, and timeframes, allowing only one repair attempt. The corrected real request passed. Real ANALYZING-stage processing persisted one topic and two actions alongside the transcript and reached `COMPLETED` in the test DB.
- Backend verification: **48 passed, 0 failed, 1 warning**; `pip check` clean; test-first migration and Alembic checks passed, and both DBs remain at `0002_ai_results` with no drift. Runtime API checks passed for health/OpenAPI, upload/history/detail, task add/edit/complete, retry, and safe failure persistence. No real Deepgram-derived transcript was persisted.
- PDF: Computer Use opened Acrobat but the accessibility tree exposed no page text. Screenshot capture showed an unrelated editor window, so automation stopped. Local stream extraction found two pages but no text; Word COM failed due the unavailable Windows logon session; no local PDF/OCR tooling was found. Requirements have **not** been freshly compared against the PDF.
- gstack launcher initialization succeeds under Git Bash; check runner stops because `bun` is unavailable. Skill checks were completed manually. The update-check subprocess crashed; no setup/upgrade was attempted because the launcher itself initialized and the requested work continued.
- Security follow-up: screenshot output inadvertently displayed the editor with `backend/.env` open. No values are recorded here and the file was unchanged. Rotate Deepgram and OmniRoute keys and the application DB role password, then update local `.env`.

**Day 2 status:** not complete until Deepgram can make a real application request and the real upload-to-completion workflow passes. PDF requirement comparison also remains open. The next frontend milestone remains the narrow React recorder/file upload, REST polling, saved results, and task editing flow.
