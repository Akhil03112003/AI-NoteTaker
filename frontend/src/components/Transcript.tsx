import { AudioLines, Clock3 } from "lucide-react";
import type { TranscriptSegment } from "../types";

function timestamp(value: number): string {
  const seconds = Math.floor(value / 1000);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}` : `${minutes}:${String(remainder).padStart(2, "0")}`;
}

export function Transcript({ segments, isProcessing }: { segments: TranscriptSegment[]; isProcessing: boolean }) {
  if (!segments.length) return <div className="transcript-empty"><AudioLines size={21} /><p>{isProcessing ? "Your transcript will appear here when transcription finishes." : "No transcript is available for this meeting."}</p></div>;
  return <div className="transcript-list">{segments.map((segment) => <article key={segment.id} className="transcript-segment">
    <div className="segment-meta">{segment.speaker_label && <span className="speaker-label">{segment.speaker_label}</span>}{segment.start_ms !== null && <span className="segment-time"><Clock3 size={12} />{timestamp(segment.start_ms)}</span>}</div>
    <p>{segment.text}</p>
  </article>)}</div>;
}
