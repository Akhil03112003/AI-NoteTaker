import { useRef, useState, type CSSProperties, type ChangeEvent, type DragEvent } from "react";
import { ArrowUpRight, AudioLines, Check, FileAudio2, LoaderCircle, Mic, Pause, Play, RotateCcw, Upload, X } from "lucide-react";
import { formatDuration, type RecorderState } from "../hooks/useRecorder";

const MAX_BYTES = 25 * 1024 * 1024;
const ACCEPTED = new Set(["mp3", "wav", "m4a", "webm"]);

interface RecordingStudioProps {
  visible: boolean;
  recorder: {
    state: RecorderState;
    take: { blob: Blob; filename: string } | null;
    elapsedMs: number;
    error: string | null;
    start: () => Promise<void>;
    pause: () => void;
    resume: () => void;
    stop: () => void;
    discard: () => void;
    clearError: () => void;
  };
  file: File | null;
  setFile: (file: File | null) => void;
  title: string;
  setTitle: (title: string) => void;
  uploading: boolean;
  uploadError: string | null;
  onUpload: () => void;
}

function validateFile(file: File): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase() || "";
  if (!ACCEPTED.has(extension)) return "Choose an MP3, WAV, M4A, or WebM audio file.";
  if (!file.size) return "This file is empty. Choose another recording.";
  if (file.size > MAX_BYTES) return "This file is over 25 MB. Choose a shorter recording.";
  const mime = file.type.toLowerCase().split(";")[0];
  const allowed: Record<string, string[]> = {
    mp3: ["audio/mpeg", "audio/mp3", "audio/x-mp3", "application/octet-stream"],
    wav: ["audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave", "application/octet-stream"],
    m4a: ["audio/mp4", "audio/m4a", "video/mp4", "application/mp4", "application/octet-stream"],
    webm: ["audio/webm", "video/webm", "application/octet-stream"],
  };
  if (mime && !allowed[extension]?.includes(mime)) return "The file extension and audio type do not match. Choose a matching audio file.";
  return null;
}

function fileSize(bytes: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(bytes / (1024 * 1024)) + " MB";
}

export function RecordingStudio({ visible, recorder, file, setFile, title, setTitle, uploading, uploadError, onUpload }: RecordingStudioProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const hasTake = Boolean(recorder.take);
  const hasSource = Boolean(file || recorder.take);

  const chooseFile = (candidate?: File) => {
    if (!candidate) return;
    if (uploading) return;
    if (["requesting", "recording", "paused", "stopping"].includes(recorder.state)) {
      setFileError("Stop or discard the current recording before choosing another file.");
      return;
    }
    const issue = validateFile(candidate);
    setFileError(issue);
    if (!issue) {
      recorder.discard();
      setFile(candidate);
    }
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    chooseFile(event.target.files?.[0]);
    event.target.value = "";
  };
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  };

  if (!visible) return null;

  return (
    <section className="studio" aria-labelledby="studio-title">
      <div className="studio-heading">
        <div className="studio-heading-copy">
          <h2 id="studio-title">Start with a conversation</h2>
          <p>Record a meeting or bring in an audio file. Your recording stays on this device until you upload it.</p>
        </div>
        <div className="record-mark" aria-hidden="true"><AudioLines size={21} strokeWidth={1.6} /></div>
      </div>

      <label className="field-label" htmlFor="meeting-title">Meeting name <span>Optional</span></label>
      <input id="meeting-title" className="text-field title-field" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} placeholder="e.g. Product planning" autoComplete="off" name="meeting-title" />

      <div className={`recording-console state-${recorder.state}`}>
        <div className="record-console-top">
          <div className="live-readout" aria-live="polite">
            <span className={`record-indicator ${recorder.state === "recording" ? "is-recording" : ""}`} />
            <span>{recorder.state === "requesting" ? "Requesting microphone" : recorder.state === "recording" ? "Recording" : recorder.state === "paused" ? "Paused" : recorder.state === "stopping" ? "Finishing recording" : hasTake ? "Recording ready" : "Microphone"}</span>
          </div>
          <time className="record-timer" aria-label={`Recording time ${formatDuration(recorder.elapsedMs)}`}>{formatDuration(recorder.elapsedMs)}</time>
        </div>
        <div className={`audio-ribbon ${recorder.state === "recording" ? "audio-ribbon-live" : ""}`} aria-hidden="true">
          {Array.from({ length: 46 }, (_, index) => <span key={index} style={{ "--bar": `${[18, 30, 12, 22, 42, 27, 15, 34, 20, 46, 18, 28, 38, 14, 24, 44, 20, 32, 15, 40, 25, 18, 48, 22, 34, 16, 29, 43, 19, 35, 14, 26, 40, 17, 32, 45, 20, 27, 13, 36, 21, 48, 16, 30, 42, 24][index]}%` } as CSSProperties} />)}
        </div>
        <div className="record-console-bottom">
          <span className="console-hint">{recorder.state === "recording" ? "Speak naturally. Pause any time." : recorder.state === "paused" ? "Your recording is paused." : "Your microphone is only used when you start."}</span>
          <div className="record-controls">
            {recorder.state === "idle" && <button className="button button-primary" onClick={() => void recorder.start()} disabled={uploading}><Mic size={16} />Start recording</button>}
            {recorder.state === "requesting" && <button className="button button-primary" disabled><LoaderCircle size={16} className="spin" />Waiting for access</button>}
            {recorder.state === "recording" && <><button className="button button-secondary" onClick={recorder.pause}><Pause size={15} />Pause</button><button className="button button-stop" onClick={recorder.stop}><span className="stop-square" />Stop</button></>}
            {recorder.state === "paused" && <><button className="button button-secondary" onClick={recorder.resume}><Play size={15} />Resume</button><button className="button button-stop" onClick={recorder.stop}><span className="stop-square" />Stop</button></>}
            {recorder.state === "stopping" && <button className="button button-secondary" disabled><LoaderCircle size={15} className="spin" />Finishing</button>}
            {recorder.state === "stopped" && hasTake && <button className="button button-secondary" onClick={recorder.discard}><RotateCcw size={15} />Record again</button>}
            {recorder.state === "stopped" && !hasTake && <button className="button button-secondary" onClick={() => void recorder.start()}><RotateCcw size={15} />Try recording again</button>}
          </div>
        </div>
      </div>

      {(recorder.error || fileError) && <p className="inline-error" role="alert">{fileError || recorder.error}</p>}
      <div className="or-divider"><span />or upload a recording<span /></div>
      <input ref={inputRef} className="visually-hidden" id="audio-upload" type="file" accept=".mp3,.wav,.m4a,.webm,audio/mpeg,audio/wav,audio/mp4,audio/webm" onChange={onFileChange} aria-label="Choose an MP3, WAV, M4A, or WebM audio file" />

      {hasSource ? (
        <div className="selected-file">
          <span className="file-icon"><FileAudio2 size={18} /></span>
          <span className="file-details"><strong>{file?.name || recorder.take?.filename}</strong><small>{file ? fileSize(file.size) : fileSize(recorder.take?.blob.size || 0)}</small></span>
          <button className="icon-button file-remove" aria-label="Discard selected recording" onClick={() => { setFile(null); recorder.discard(); setFileError(null); }} disabled={uploading}><X size={16} /></button>
        </div>
      ) : (
        <div className={`dropzone ${dragging ? "dropzone-active" : ""}`} onDragOver={(event) => { event.preventDefault(); if (!uploading) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
          <span className="drop-icon"><Upload size={17} /></span>
          <span><strong>Choose an audio file</strong><small>MP3, WAV, M4A, or WebM · up to 25 MB</small></span>
          <button type="button" className="button button-secondary choose-button" onClick={() => inputRef.current?.click()}>Browse files</button>
        </div>
      )}

      {uploadError && <p className="inline-error upload-error" role="alert">{uploadError} Your recording is still here; retry the upload or choose another file.</p>}
      {hasSource && <div className="upload-footer">
        <p>Only the audio you choose is uploaded. Provider credentials stay on the server.</p>
        <button className="button button-primary upload-button" onClick={onUpload} disabled={uploading}>
          {uploading ? <><LoaderCircle size={16} className="spin" />Uploading</> : <><span>Upload &amp; create notes</span><ArrowUpRight size={16} /></>}
        </button>
      </div>}
      {!hasSource && <p className="privacy-note"><Check size={13} />Your recording stays local until you choose to upload.</p>}
      {uploading && <p className="uploading-note" role="status">Uploading your recording… Keep this page open until it finishes.</p>}
    </section>
  );
}
