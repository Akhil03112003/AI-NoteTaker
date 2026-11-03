import type {
  ActionItem,
  ActionItemInput,
  ActionItemPatch,
  ApiErrorPayload,
  SessionCreated,
  SessionDetail,
  SessionHistory,
} from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function expectShape<T>(value: unknown, predicate: (candidate: Record<string, unknown>) => boolean): T {
  if (!isRecord(value) || !predicate(value)) {
    throw new ApiError("The server returned an unexpected response. Refresh the page and try again.", "invalid_response", 200);
  }
  return value as T;
}

const isString = (value: unknown): value is string => typeof value === "string";
const isStatus = (value: unknown): value is string => ["UPLOADED", "TRANSCRIBING", "ANALYZING", "COMPLETED", "FAILED"].includes(String(value));
const isNullableNumber = (value: unknown) => value === null || typeof value === "number";
const isNullableString = (value: unknown) => value === null || typeof value === "string";

function isActionItem(value: unknown): boolean {
  return isRecord(value) && isString(value.id) && isString(value.session_id) && typeof value.ordinal === "number" &&
    isString(value.description) && isString(value.assignee) && isNullableString(value.due_date) && isNullableString(value.timeframe) &&
    ["High", "Medium", "Low"].includes(String(value.priority)) && typeof value.is_completed === "boolean";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new ApiError("Can't reach the notetaker server. Check that the backend is running, then try again.", "network_error", 0);
  }

  const body = await response.json().catch(() => null) as ApiErrorPayload | T | null;
  if (!response.ok) {
    const errorBody = body as ApiErrorPayload | null;
    const status = response.status;
    const fallback = status === 404
      ? "This meeting could not be found. Refresh your meeting list and try again."
      : status === 413
        ? "This recording is too large. Choose an audio file under 25 MB."
        : status === 415
          ? "This audio file could not be accepted. Check its format and try another recording."
          : "The request could not be completed. Try again.";
    throw new ApiError(errorBody?.error?.message || fallback, errorBody?.error?.code || "request_failed", status);
  }
  if (body === null) throw new ApiError("The server returned an unreadable response. Try again.", "invalid_response", response.status);
  return body as T;
}

export function getSessions(offset = 0, limit = 20): Promise<SessionHistory> {
  return request<unknown>(`/api/sessions?limit=${limit}&offset=${offset}`).then((value) => expectShape<SessionHistory>(value, (body) =>
    Array.isArray(body.items) && typeof body.total === "number" && typeof body.limit === "number" && typeof body.offset === "number" &&
    body.items.every((item) => isRecord(item) && isString(item.id) && isString(item.title) && isStatus(item.status) && isString(item.created_at) && typeof item.file_size_bytes === "number"),
  ));
}

export function getSession(sessionId: string): Promise<SessionDetail> {
  return request<unknown>(`/api/sessions/${encodeURIComponent(sessionId)}`).then((value) => expectShape<SessionDetail>(value, (body) =>
    isString(body.id) && isString(body.title) && isStatus(body.status) && isString(body.created_at) && isString(body.updated_at) &&
    isString(body.original_filename) && isString(body.media_type) && typeof body.file_size_bytes === "number" && isNullableNumber(body.duration_ms) &&
    isNullableString(body.safe_error_code) && isNullableString(body.failed_stage) &&
    Array.isArray(body.transcript_segments) && body.transcript_segments.every((segment) => isRecord(segment) && isString(segment.id) && typeof segment.ordinal === "number" && isString(segment.text) && isNullableString(segment.speaker_label) && isNullableNumber(segment.start_ms) && isNullableNumber(segment.end_ms)) &&
    Array.isArray(body.topics) && body.topics.every((topic) => isRecord(topic) && isString(topic.id) && typeof topic.ordinal === "number" && isString(topic.title) && isString(topic.summary)) &&
    Array.isArray(body.action_items) && body.action_items.every(isActionItem),
  ));
}

export function uploadSession(file: File | Blob, filename: string, title: string): Promise<SessionCreated> {
  const form = new FormData();
  form.append("file", file, filename);
  if (title.trim()) form.append("title", title.trim());
  return request<unknown>("/api/sessions", { method: "POST", body: form }).then((value) => expectShape<SessionCreated>(value, (body) =>
    isString(body.id) && isString(body.title) && isString(body.status) && isString(body.created_at),
  ));
}

export function addActionItem(sessionId: string, input: ActionItemInput): Promise<ActionItem> {
  return request<unknown>(`/api/sessions/${encodeURIComponent(sessionId)}/action-items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }).then((value) => expectShape<ActionItem>(value, isActionItem));
}

export function updateActionItem(actionId: string, input: ActionItemPatch): Promise<ActionItem> {
  return request<unknown>(`/api/action-items/${encodeURIComponent(actionId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  }).then((value) => expectShape<ActionItem>(value, isActionItem));
}

export function retrySession(sessionId: string): Promise<{ id: string; status: string }> {
  return request<unknown>(`/api/sessions/${encodeURIComponent(sessionId)}/retry`, { method: "POST" }).then((value) => expectShape<{ id: string; status: string }>(value, (body) => isString(body.id) && isString(body.status)));
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Try again.";
}

export function friendlyFailure(code: string | null): string {
  const messages: Record<string, string> = {
    transcription_network_error: "The transcription service could not be reached. Your recording is saved; retry processing when the connection is available.",
    transcription_auth_failed: "The transcription service could not authenticate this request. Contact the workspace administrator.",
    transcription_rate_limited: "The transcription service is busy. Wait a moment, then retry this meeting.",
    transcription_timeout: "Transcription took too long. Check your connection, then retry.",
    transcription_unsupported_audio: "The transcription service rejected this audio format. Try an MP3, WAV, M4A, or WebM recording.",
    transcription_empty: "No speech was detected in this recording. Try another file or record again.",
    transcription_not_configured: "Transcription is not configured on the backend. Contact the workspace administrator.",
    analysis_network_error: "The notes service could not be reached. Your transcript is saved; retry to generate notes.",
    analysis_auth_failed: "The notes service could not authenticate this request. Contact the workspace administrator.",
    analysis_rate_limited: "The notes service is busy. Wait a moment, then retry this meeting.",
    analysis_timeout: "Generating notes took too long. Retry this meeting in a moment.",
    analysis_invalid_output: "The notes service returned notes that did not match the required format. Retry this meeting.",
    analysis_not_configured: "AI notes are not configured on the backend. Contact the workspace administrator.",
  };
  return messages[code || ""] || "This meeting could not be processed. Your saved recording is available to retry.";
}
