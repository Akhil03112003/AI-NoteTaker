"""Smoke-test Deepgram Listen v1 with samples/deepgram-test.wav."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from deepgram import DeepgramClient
from deepgram.core.api_error import ApiError
from dotenv import dotenv_values
import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / "backend" / ".env"
AUDIO_FILE = PROJECT_ROOT / "samples" / "deepgram-test.wav"


def field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def failure(message: str, elapsed: float = 0.0) -> int:
    print(f"Request: NOT SENT - {message}")
    print(f"Elapsed: {elapsed:.3f} s")
    return 1


def http_error_message(status_code: int | None) -> str:
    messages = {
        400: "Deepgram rejected the audio or request options.",
        401: "Authentication failed; check the configured key.",
        403: "The key does not have permission for this request.",
        404: "The requested endpoint or model was not found.",
        413: "The audio file is too large for the request.",
        429: "Rate limit or account quota was reached.",
    }
    if status_code in messages:
        return messages[status_code]
    if status_code is not None and status_code >= 500:
        return "Deepgram returned a server error."
    return "Deepgram returned an HTTP error."


def extract_transcript(response: Any) -> str:
    results = field(response, "results")
    channels = field(results, "channels")
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("response has no results.channels entry")

    alternatives = field(channels[0], "alternatives")
    if not isinstance(alternatives, (list, tuple)) or not alternatives:
        raise ValueError("response has no channel alternatives")

    transcript = field(alternatives[0], "transcript")
    if not isinstance(transcript, str):
        raise ValueError("response transcript is missing or not text")
    return transcript


def main() -> int:
    if not ENV_FILE.is_file():
        return failure("backend/.env was not found")

    try:
        api_key = dotenv_values(ENV_FILE, encoding="utf-8").get("DEEPGRAM_API_KEY")
    except (OSError, UnicodeError):
        return failure("could not read backend/.env")

    if not isinstance(api_key, str) or not api_key.strip():
        return failure("DEEPGRAM_API_KEY is missing or empty in backend/.env")

    if not AUDIO_FILE.is_file():
        return failure("samples/deepgram-test.wav was not found")

    try:
        audio = AUDIO_FILE.read_bytes()
    except OSError:
        return failure("could not read samples/deepgram-test.wav")

    started = time.perf_counter()
    try:
        client = DeepgramClient(api_key=api_key)
        response = client.listen.v1.media.transcribe_file(
            request=audio,
            model="nova-3",
            smart_format=True,
        )
        transcript = extract_transcript(response)
    except ApiError as exc:
        elapsed = time.perf_counter() - started
        status_code = getattr(exc, "status_code", None)
        status_text = f"HTTP {status_code}: " if isinstance(status_code, int) else "HTTP error: "
        print(f"Request: FAILED - {status_text}{http_error_message(status_code)}")
        print(f"Elapsed: {elapsed:.3f} s")
        return 1
    except httpx.HTTPError as exc:
        elapsed = time.perf_counter() - started
        print(f"Request: FAILED - network error ({type(exc).__name__})")
        print(f"Elapsed: {elapsed:.3f} s")
        return 1
    except ValueError as exc:
        elapsed = time.perf_counter() - started
        print(f"Request: FAILED - malformed Deepgram response ({exc})")
        print(f"Elapsed: {elapsed:.3f} s")
        return 1
    except Exception as exc:  # Keep SDK/transport details and credentials out of output.
        elapsed = time.perf_counter() - started
        print(f"Request: FAILED - unexpected error ({type(exc).__name__})")
        print(f"Elapsed: {elapsed:.3f} s")
        return 1

    elapsed = time.perf_counter() - started
    print("Request: SUCCESS")
    print(f"Elapsed: {elapsed:.3f} s")
    print("Transcription:")
    print(transcript)
    return 0


if __name__ == "__main__":
    sys.exit(main())
