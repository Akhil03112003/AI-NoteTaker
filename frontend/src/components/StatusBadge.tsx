import { Check, Circle, LoaderCircle, TriangleAlert } from "lucide-react";
import type { ProcessingStatus } from "../types";

const labels: Record<ProcessingStatus, string> = {
  UPLOADED: "Queued",
  TRANSCRIBING: "Transcribing",
  ANALYZING: "Writing notes",
  COMPLETED: "Ready",
  FAILED: "Needs attention",
};

export function StatusBadge({ status, compact = false }: { status: ProcessingStatus; compact?: boolean }) {
  const icon = status === "COMPLETED" ? <Check size={12} aria-hidden="true" />
    : status === "FAILED" ? <TriangleAlert size={12} aria-hidden="true" />
      : status === "UPLOADED" ? <Circle size={8} aria-hidden="true" />
        : <LoaderCircle size={12} className="spin" aria-hidden="true" />;
  return <span className={`status status-${status.toLowerCase()}${compact ? " status-compact" : ""}`}>{icon}<span>{labels[status]}</span></span>;
}

export function statusDescription(status: ProcessingStatus): string {
  switch (status) {
    case "UPLOADED": return "Your audio is in the queue.";
    case "TRANSCRIBING": return "Turning the recording into a transcript…";
    case "ANALYZING": return "Finding topics and follow-ups…";
    case "COMPLETED": return "Your transcript and notes are ready.";
    case "FAILED": return "Processing stopped. Your saved audio is ready to retry.";
  }
}
