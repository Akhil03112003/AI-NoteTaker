export type ProcessingStatus =
  | "UPLOADED"
  | "TRANSCRIBING"
  | "ANALYZING"
  | "COMPLETED"
  | "FAILED";

export interface SessionHistoryItem {
  id: string;
  title: string;
  status: ProcessingStatus;
  created_at: string;
  file_size_bytes: number;
}

export interface SessionHistory {
  items: SessionHistoryItem[];
  limit: number;
  offset: number;
  total: number;
}

export interface TranscriptSegment {
  id: string;
  ordinal: number;
  text: string;
  speaker_label: string | null;
  start_ms: number | null;
  end_ms: number | null;
}

export interface Topic {
  id: string;
  ordinal: number;
  title: string;
  summary: string;
}

export type Priority = "High" | "Medium" | "Low";

export interface ActionItem {
  id: string;
  session_id: string;
  ordinal: number;
  description: string;
  assignee: string;
  due_date: string | null;
  timeframe: string | null;
  priority: Priority;
  is_completed: boolean;
}

export interface SessionDetail {
  id: string;
  title: string;
  original_filename: string;
  media_type: string;
  file_size_bytes: number;
  duration_ms: number | null;
  status: ProcessingStatus;
  created_at: string;
  updated_at: string;
  safe_error_code: string | null;
  failed_stage: "TRANSCRIBING" | "ANALYZING" | null;
  transcript_segments: TranscriptSegment[];
  topics: Topic[];
  action_items: ActionItem[];
}

export interface SessionCreated {
  id: string;
  title: string;
  status: ProcessingStatus;
  created_at: string;
}

export interface ActionItemInput {
  description: string;
  assignee?: string;
  due_date?: string | null;
  timeframe?: string | null;
  priority?: Priority;
}

export type ActionItemPatch = Partial<ActionItemInput> & {
  is_completed?: boolean;
};

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
}
