import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useRecorder } from "./useRecorder";

class FakeMediaRecorder {
  static isTypeSupported() { return true; }
  state: RecordingState = "inactive";
  mimeType = "audio/webm";
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(_stream: MediaStream, _options?: MediaRecorderOptions) {}
  start() { this.state = "recording"; }
  pause() { this.state = "paused"; }
  resume() { this.state = "recording"; }
  stop() {
    this.state = "inactive";
    this.onstop?.();
  }
  fail() { this.onerror?.(); }
}

function RecorderHarness() {
  const recorder = useRecorder();
  return createElement("button", { onClick: () => void recorder.start() }, recorder.state);
}

describe("useRecorder", () => {
  let root: Root | null = null;
  let container: HTMLDivElement | null = null;
  let streams: MediaStream[] = [];
  let recorders: FakeMediaRecorder[] = [];
  let mediaRecorderDescriptor: PropertyDescriptor | undefined;
  let mediaDevicesDescriptor: PropertyDescriptor | undefined;
  let actEnvironmentDescriptor: PropertyDescriptor | undefined;

  beforeEach(() => {
    mediaRecorderDescriptor = Object.getOwnPropertyDescriptor(globalThis, "MediaRecorder");
    mediaDevicesDescriptor = Object.getOwnPropertyDescriptor(navigator, "mediaDevices");
    actEnvironmentDescriptor = Object.getOwnPropertyDescriptor(globalThis, "IS_REACT_ACT_ENVIRONMENT");
  });

  afterEach(() => {
    if (root) act(() => root?.unmount());
    root = null;
    container?.remove();
    container = null;
    streams = [];
    recorders = [];
    if (mediaRecorderDescriptor) Object.defineProperty(globalThis, "MediaRecorder", mediaRecorderDescriptor);
    else Reflect.deleteProperty(globalThis, "MediaRecorder");
    if (mediaDevicesDescriptor) Object.defineProperty(navigator, "mediaDevices", mediaDevicesDescriptor);
    else Reflect.deleteProperty(navigator, "mediaDevices");
    if (actEnvironmentDescriptor) Object.defineProperty(globalThis, "IS_REACT_ACT_ENVIRONMENT", actEnvironmentDescriptor);
    else Reflect.deleteProperty(globalThis, "IS_REACT_ACT_ENVIRONMENT");
    vi.restoreAllMocks();
  });

  it("restarts after a recorder error without reusing the stopped state", async () => {
    Object.defineProperty(globalThis, "IS_REACT_ACT_ENVIRONMENT", { configurable: true, value: true });
    Object.defineProperty(globalThis, "MediaRecorder", {
      configurable: true,
      value: class extends FakeMediaRecorder {
        constructor(stream: MediaStream, options?: MediaRecorderOptions) {
          super(stream, options);
          recorders.push(this);
        }
      },
    });
    const getUserMedia = vi.fn(async () => {
      const stream = {
        getTracks: () => [{ stop: vi.fn() }],
      } as unknown as MediaStream;
      streams.push(stream);
      return stream;
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia },
    });

    container = document.createElement("div");
    document.body.append(container);
    root = createRoot(container);
    await act(async () => { root?.render(createElement(RecorderHarness)); });

    const button = container.querySelector("button")!;
    await act(async () => { button.click(); await Promise.resolve(); });
    expect(button.textContent).toBe("recording");

    await act(async () => { recorders[0]!.fail(); });
    expect(button.textContent).toBe("stopped");

    await act(async () => { button.click(); await Promise.resolve(); });
    expect(button.textContent).toBe("recording");
    expect(getUserMedia).toHaveBeenCalledTimes(2);
    expect(streams[0]).not.toBe(streams[1]);

    await act(async () => { recorders[1]!.stop(); });
  });
});
