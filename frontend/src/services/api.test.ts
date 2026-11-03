import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getSession, getSessions } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("typed API client", () => {
  it("accepts the implemented session-history envelope", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      items: [{ id: "meeting-1", title: "Planning", status: "COMPLETED", created_at: "2026-11-03T10:00:00Z", file_size_bytes: 2048 }],
      limit: 20,
      offset: 0,
      total: 1,
    }), { status: 200, headers: { "Content-Type": "application/json" } })));

    await expect(getSessions()).resolves.toMatchObject({ total: 1, items: [{ title: "Planning" }] });
    expect(fetch).toHaveBeenCalledWith("http://127.0.0.1:8000/api/sessions?limit=20&offset=0", undefined);
  });

  it("rejects an unexpected detail response rather than rendering it as a session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "meeting-1", transcript_segments: "wrong-shape" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));

    await expect(getSession("meeting-1")).rejects.toMatchObject({ code: "invalid_response" });
  });

  it("preserves the backend safe error code and message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: "session_not_found", message: "No session exists with that ID." },
    }), { status: 404, headers: { "Content-Type": "application/json" } })));

    await expect(getSession("missing")).rejects.toEqual(expect.objectContaining<ApiError>({
      name: "ApiError",
      code: "session_not_found",
      status: 404,
      message: "No session exists with that ID.",
    }));
  });
});
