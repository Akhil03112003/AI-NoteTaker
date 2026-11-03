import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderState = "idle" | "requesting" | "recording" | "paused" | "stopping" | "stopped";

interface RecordingTake {
  blob: Blob;
  filename: string;
}

function recordingFormat(): { mimeType?: string; extension: string } {
  if (typeof MediaRecorder === "undefined") throw new Error("This browser does not support audio recording. Upload an audio file instead.");
  const formats = [
    { mimeType: "audio/webm;codecs=opus", extension: "webm" },
    { mimeType: "audio/webm", extension: "webm" },
    { mimeType: "audio/mp4", extension: "m4a" },
  ];
  const match = formats.find((format) => MediaRecorder.isTypeSupported(format.mimeType));
  if (!match) throw new Error("This browser cannot record MP4 or WebM audio. Upload an MP3, WAV, M4A, or WebM file instead.");
  return match;
}

export function useRecorder() {
  const [state, setState] = useState<RecorderState>("idle");
  const [take, setTake] = useState<RecordingTake | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const startAtRef = useRef<number | null>(null);
  const elapsedBeforeRef = useRef(0);
  const extensionRef = useRef("webm");

  const releaseStream = useCallback((stream: MediaStream) => {
    stream.getTracks().forEach((track) => track.stop());
    if (streamRef.current === stream) streamRef.current = null;
  }, []);

  const releaseTracks = useCallback(() => {
    const stream = streamRef.current;
    if (stream) releaseStream(stream);
  }, [releaseStream]);

  const start = useCallback(async () => {
    const retryingWithoutTake = state === "stopped" && take === null;
    if (state !== "idle" && !retryingWithoutTake) return;
    if (retryingWithoutTake) {
      const previousRecorder = recorderRef.current;
      recorderRef.current = null;
      if (previousRecorder && previousRecorder.state !== "inactive") previousRecorder.stop();
      releaseTracks();
    }
    setError(null);
    setState("requesting");
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("Microphone access is unavailable in this browser. Upload an audio file instead.");
      const format = recordingFormat();
      extensionRef.current = format.extension;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = format.mimeType ? new MediaRecorder(stream, { mimeType: format.mimeType }) : new MediaRecorder(stream);
      const chunks: BlobPart[] = [];
      elapsedBeforeRef.current = 0;
      setElapsedMs(0);
      setTake(null);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };
      recorder.onstop = () => {
        if (recorderRef.current !== recorder) { releaseStream(stream); return; }
        const blob = new Blob(chunks, { type: recorder.mimeType || `audio/${extensionRef.current}` });
        setTake({ blob, filename: `meeting-recording.${extensionRef.current}` });
        setElapsedMs(elapsedBeforeRef.current);
        setState("stopped");
        releaseStream(stream);
      };
      recorder.onerror = () => {
        if (recorderRef.current !== recorder) { releaseStream(stream); return; }
        setError("Recording stopped unexpectedly. Try again or choose an audio file.");
        setState("stopped");
        releaseStream(stream);
      };
      recorderRef.current = recorder;
      recorder.start(1000);
      startAtRef.current = Date.now();
      setState("recording");
    } catch (reason) {
      releaseTracks();
      setState("idle");
      const name = reason instanceof DOMException ? reason.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setError("Microphone access was denied. Allow microphone access in your browser settings or upload an audio file.");
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setError("No microphone was found. Connect a microphone or upload an audio file.");
      } else if (reason instanceof Error) {
        setError(reason.message);
      } else {
        setError("The recording could not be started. Check your microphone and try again.");
      }
    }
  }, [releaseStream, releaseTracks, state, take]);

  const pause = useCallback(() => {
    const recorder = recorderRef.current;
    if (state !== "recording" || !recorder || recorder.state !== "recording") return;
    elapsedBeforeRef.current += Date.now() - (startAtRef.current || Date.now());
    startAtRef.current = null;
    recorder.pause();
    setElapsedMs(elapsedBeforeRef.current);
    setState("paused");
  }, [state]);

  const resume = useCallback(() => {
    const recorder = recorderRef.current;
    if (state !== "paused" || !recorder || recorder.state !== "paused") return;
    startAtRef.current = Date.now();
    recorder.resume();
    setState("recording");
  }, [state]);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || (state !== "recording" && state !== "paused")) return;
    if (startAtRef.current) elapsedBeforeRef.current += Date.now() - startAtRef.current;
    startAtRef.current = null;
    recorder.stop();
    setState("stopping");
  }, [state]);

  const discard = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state !== "inactive") recorderRef.current.stop();
    recorderRef.current = null;
    releaseTracks();
    recorderRef.current = null;
    elapsedBeforeRef.current = 0;
    startAtRef.current = null;
    setElapsedMs(0);
    setTake(null);
    setError(null);
    setState("idle");
  }, [releaseTracks]);

  useEffect(() => {
    if (state !== "recording") return;
    const interval = window.setInterval(() => {
      setElapsedMs(elapsedBeforeRef.current + (Date.now() - (startAtRef.current || Date.now())));
    }, 250);
    return () => window.clearInterval(interval);
  }, [state]);

  useEffect(() => () => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    releaseTracks();
  }, [releaseTracks]);

  return { state, take, elapsedMs, error, start, pause, resume, stop, discard, clearError: () => setError(null) };
}

export function formatDuration(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds].map((part) => String(part).padStart(2, "0")).join(":");
}
