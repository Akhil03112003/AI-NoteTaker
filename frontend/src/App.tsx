import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type MouseEvent, type ReactNode } from "react";
import {
  ArrowLeft, ArrowRight, AudioLines, CalendarDays, ChevronDown, ChevronRight,
  CircleHelp, Clock3, FileAudio2, Headphones, ListMusic, LoaderCircle, Menu, Mic2,
  Plus, RefreshCw, Search, Sparkles, X,
} from "lucide-react";
import { ActionItems } from "./components/ActionItems";
import { RecordingStudio } from "./components/RecordingStudio";
import { StatusBadge, statusDescription } from "./components/StatusBadge";
import { Transcript } from "./components/Transcript";
import { useRecorder, formatDuration } from "./hooks/useRecorder";
import {
  addActionItem, ApiError, errorMessage, friendlyFailure, getSession, getSessions,
  retrySession, updateActionItem, uploadSession,
} from "./services/api";
import type { ActionItem, ActionItemInput, ProcessingStatus, SessionDetail, SessionHistoryItem } from "./types";

type Route = { view: "home" | "meetings" | "new" | "session"; sessionId?: string };
type ResultTab = "insights" | "transcript";

function routeFromLocation(): Route {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get("session");
  if (sessionId) return { view: "session", sessionId };
  const view = params.get("view");
  if (view === "new" || view === "meetings") return { view };
  return { view: "home" };
}

function routeHref(route: Route): string {
  if (route.sessionId) return `?session=${encodeURIComponent(route.sessionId)}`;
  if (route.view === "home") return "/";
  return `?view=${route.view}`;
}

function useRoute() {
  const [route, setRoute] = useState(routeFromLocation);
  useEffect(() => {
    const onPopState = () => setRoute(routeFromLocation());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  const navigate = useCallback((next: Route) => {
    window.history.pushState(null, "", routeHref(next));
    setRoute(next);
  }, []);
  return { route, navigate };
}

function formatDate(value: string, options: Intl.DateTimeFormatOptions = { month: "short", day: "numeric", year: "numeric" }): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : new Intl.DateTimeFormat(undefined, options).format(date);
}

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${new Intl.NumberFormat().format(Math.max(1, Math.round(bytes / 1024)))} KB`;
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(bytes / (1024 * 1024))} MB`;
}

function shortTime(value: string): string {
  return formatDate(value, { month: "short", day: "numeric" });
}

function processingAge(value: string): string {
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  return formatDuration(elapsed);
}

function MeetingLink({ item, active, onNavigate }: { item: SessionHistoryItem; active: boolean; onNavigate: () => void }) {
  return <a href={routeHref({ view: "session", sessionId: item.id })} className={`meeting-link${active ? " meeting-link-active" : ""}`} onClick={(event) => { event.preventDefault(); onNavigate(); }}>
    <span className="meeting-link-icon"><FileAudio2 size={15} /></span>
    <span className="meeting-link-copy"><strong>{item.title}</strong><small>{shortTime(item.created_at)}</small></span>
    <span className="meeting-link-status" aria-label={item.status}><span className={`status-dot status-dot-${item.status.toLowerCase()}`} /></span>
  </a>;
}

function Shell({ children, route, historyItems, total, loadingHistory, historyError, onNavigate, onLoadMore, mobileOpen, setMobileOpen, onRefreshHistory }: {
  children: ReactNode;
  route: Route;
  historyItems: SessionHistoryItem[];
  total: number;
  loadingHistory: boolean;
  historyError: string | null;
  onNavigate: (route: Route) => void;
  onLoadMore: () => void;
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  onRefreshHistory: () => void;
}) {
  const isActive = (view: Route["view"]) => route.view === view || (view === "meetings" && route.view === "session");
  const link = (next: Route) => (event: MouseEvent<HTMLAnchorElement>) => { event.preventDefault(); onNavigate(next); setMobileOpen(false); };

  return <div className="app-shell">
    <aside className={`sidebar${mobileOpen ? " sidebar-open" : ""}`} aria-label="Main navigation">
      <div className="brand-row">
        <span className="brand-mark" aria-hidden="true"><AudioLines size={20} strokeWidth={1.7} /></span>
        <span className="brand-name">AI Notetaker</span>
        <button className="icon-button sidebar-close" aria-label="Close navigation" onClick={() => setMobileOpen(false)}><X size={18} /></button>
      </div>
      <div className="workspace-switcher"><span className="workspace-avatar">A</span><span><strong>Personal workspace</strong><small>Meeting notes</small></span><ChevronDown size={14} /></div>
      <a className="new-meeting-button" href="?view=new" onClick={link({ view: "new" })}><span><Plus size={15} />New meeting</span><kbd>N</kbd></a>
      <nav className="primary-nav" aria-label="Workspace">
        <p className="nav-caption">Workspace</p>
        <a href="/" className={`nav-link${isActive("home") ? " nav-link-active" : ""}`} onClick={link({ view: "home" })}><AudioLines size={16} /><span>Overview</span></a>
        <a href="?view=meetings" className={`nav-link${isActive("meetings") ? " nav-link-active" : ""}`} onClick={link({ view: "meetings" })}><ListMusic size={16} /><span>All meetings</span>{total > 0 && <span className="nav-count">{total}</span>}</a>
      </nav>
      <div className="history-nav">
        <div className="history-nav-heading"><p className="nav-caption">Recent meetings</p><button className="icon-button tiny" aria-label="Refresh meeting history" onClick={onRefreshHistory}><RefreshCw size={13} /></button></div>
        {historyError ? <div className="sidebar-message"><span>Meeting history is unavailable.</span><button className="text-action" onClick={onRefreshHistory}>Retry</button></div> : loadingHistory && historyItems.length === 0 ? <div className="history-loading" aria-label="Loading meeting history"><span /><span /><span /></div> : historyItems.length === 0 ? <p className="sidebar-empty">Your recordings will show up here.</p> : <div className="history-links">{historyItems.slice(0, 8).map((item) => <MeetingLink key={item.id} item={item} active={route.sessionId === item.id} onNavigate={() => { onNavigate({ view: "session", sessionId: item.id }); setMobileOpen(false); }} />)}</div>}
        {historyItems.length < total && <button className="load-more-link" onClick={onLoadMore}>Load older meetings <ChevronRight size={13} /></button>}
      </div>
      <div className="sidebar-bottom"><div className="sidebar-tip"><span className="tip-mark"><Sparkles size={14} /></span><p><strong>Good notes start with a good conversation.</strong><small>Record or upload to get a transcript and follow-ups.</small></p></div><div className="workspace-footer"><span className="online-dot" /><span>Private workspace</span><span className="footer-version">v0.1</span></div></div>
    </aside>
    {mobileOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <div className="workspace-main">
      <header className="mobile-topbar"><button className="icon-button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={19} /></button><a className="mobile-brand" href="/" onClick={link({ view: "home" })}><AudioLines size={18} />AI Notetaker</a><a className="mobile-new" href="?view=new" onClick={link({ view: "new" })}><Plus size={16} /><span>New</span></a></header>
      <div className="main-canvas">{children}</div>
    </div>
  </div>;
}

function PageTitle({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return <div className="page-title-row"><div className="page-title-copy"><h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="title-actions">{action}</div>}</div>;
}

function MeetingRow({ item, onOpen }: { item: SessionHistoryItem; onOpen: () => void }) {
  return <a className="meeting-row" href={routeHref({ view: "session", sessionId: item.id })} onClick={(event) => { event.preventDefault(); onOpen(); }}>
    <span className="meeting-row-mark"><AudioLines size={17} /></span>
    <span className="meeting-row-name"><strong>{item.title}</strong><small><CalendarDays size={12} />{formatDate(item.created_at, { weekday: "short", month: "short", day: "numeric", year: "numeric" })}<span className="meta-dot">·</span>{formatBytes(item.file_size_bytes)}</small></span>
    <StatusBadge status={item.status} compact />
    <ArrowRight className="row-arrow" size={15} />
  </a>;
}

function HomeView({ sessions, total, loading, error, onNew, onMeetings, onOpen, onRetry }: {
  sessions: SessionHistoryItem[];
  total: number;
  loading: boolean;
  error: string | null;
  onNew: () => void;
  onMeetings: () => void;
  onOpen: (id: string) => void;
  onRetry: () => void;
}) {
  return <div className="home-view page-enter">
    <PageTitle title="Overview" description="One place for the conversations you want to remember." action={<button className="button button-primary" onClick={onNew}><Plus size={16} />New meeting</button>} />
    <section className="home-feature" aria-labelledby="home-feature-title">
      <div className="home-feature-copy"><div className="feature-icon"><AudioLines size={19} /></div><h2 id="home-feature-title">Make room for the conversation.</h2><p>Record a discussion or upload audio. Your transcript, topic notes, and next steps come together here.</p><button className="button button-primary" onClick={onNew}><Mic2 size={16} />Start a meeting<ArrowRight size={15} /></button></div>
      <div className="feature-wave" aria-hidden="true"><div className="wave-label"><span>Conversation</span><span>Notes that move work forward</span></div><div className="wave-line">{Array.from({ length: 52 }, (_, index) => <i key={index} style={{ "--wave": `${[13, 22, 31, 19, 38, 54, 25, 66, 42, 74, 34, 58, 23, 46, 69, 36, 57, 27, 81, 50, 31, 64, 42, 78, 28, 50, 72, 33, 57, 22, 47, 70, 40, 60, 29, 78, 45, 25, 54, 72, 36, 62, 19, 45, 66, 30, 56, 40, 76, 27, 49, 20][index]}%` } as CSSProperties} />)}</div><div className="wave-foot"><span>TRANSCRIPT</span><span>TOPICS</span><span>NEXT STEPS</span></div></div>
    </section>
    <section className="recent-section" aria-labelledby="recent-title">
      <div className="section-heading"><div><h2 id="recent-title">Recent meetings</h2><p>{total ? `${total} saved ${total === 1 ? "conversation" : "conversations"}` : "Your saved conversations will live here."}</p></div>{total > 5 && <button className="text-action" onClick={onMeetings}>View all <ArrowRight size={14} /></button>}</div>
      {error ? <div className="content-error"><p>{error}</p><button className="text-action" onClick={onRetry}>Try again</button></div> : loading && sessions.length === 0 ? <div className="meeting-skeletons"><span /><span /><span /></div> : sessions.length === 0 ? <div className="home-empty"><span className="empty-line"><FileAudio2 size={17} /></span><p>No meetings yet. Start a recording or upload a file to create your first set of notes.</p><button className="button button-secondary" onClick={onNew}>Create your first meeting</button></div> : <div className="meeting-list">{sessions.slice(0, 5).map((item) => <MeetingRow key={item.id} item={item} onOpen={() => onOpen(item.id)} />)}</div>}
    </section>
    <footer className="home-footer"><span>Built for the details worth keeping.</span><span><CircleHelp size={13} />Audio is processed by your configured backend providers.</span></footer>
  </div>;
}

function LibraryView({ sessions, total, loading, error, offset, pageSize, onOpen, onRetry, onLoadMore, onNew }: {
  sessions: SessionHistoryItem[];
  total: number;
  loading: boolean;
  error: string | null;
  offset: number;
  pageSize: number;
  onOpen: (id: string) => void;
  onRetry: () => void;
  onLoadMore: () => void;
  onNew: () => void;
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => sessions.filter((item) => item.title.toLowerCase().includes(query.trim().toLowerCase())), [query, sessions]);
  return <div className="library-view page-enter">
    <PageTitle title="All meetings" description={`${total} ${total === 1 ? "conversation" : "conversations"} saved in your workspace.`} action={<button className="button button-primary" onClick={onNew}><Plus size={16} />New meeting</button>} />
    <div className="library-toolbar"><div className="search-field"><Search size={16} /><label className="sr-only" htmlFor="meeting-search">Search meetings</label><input id="meeting-search" name="meeting-search" autoComplete="off" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search meetings…" /></div><span className="library-range">Showing {sessions.length ? offset + 1 : 0}–{Math.min(offset + sessions.length, total)} of {total}</span></div>
    {error ? <div className="content-error"><p>{error}</p><button className="text-action" onClick={onRetry}>Try again</button></div> : loading && sessions.length === 0 ? <div className="meeting-skeletons"><span /><span /><span /><span /></div> : filtered.length === 0 ? <div className="library-empty"><FileAudio2 size={20} /><h2>{query ? "No meetings match that search" : "Your library is ready"}</h2><p>{query ? "Try a different title." : "Record a conversation or upload audio to see it here."}</p>{!query && <button className="button button-secondary" onClick={onNew}>Create a meeting</button>}</div> : <div className="meeting-list library-list">{filtered.map((item) => <MeetingRow key={item.id} item={item} onOpen={() => onOpen(item.id)} />)}</div>}
    {offset + pageSize < total && <div className="load-more-wrap"><button className="button button-secondary" onClick={onLoadMore} disabled={loading}>{loading ? <LoaderCircle size={15} className="spin" /> : <ChevronDown size={15} />}Load older meetings</button></div>}
  </div>;
}

function TopicSummary({ topics, status }: { topics: SessionDetail["topics"]; status: ProcessingStatus }) {
  return <section className="topic-section" aria-labelledby="summary-title"><div className="section-heading"><div><h2 id="summary-title">Discussion themes</h2><p>Key topics from this conversation</p></div></div>
    {topics.length ? <div className="topic-list">{topics.map((topic) => <article className="topic-item" key={topic.id}><span className="topic-mark" aria-hidden="true" /><div><h3>{topic.title}</h3><p>{topic.summary}</p></div></article>)}</div> : <div className="topic-empty"><p>{status === "ANALYZING" ? "Topic notes will appear here as analysis finishes." : status === "FAILED" ? "Topic notes are not available for this meeting." : "Discussion themes will appear here after analysis."}</p></div>}
  </section>;
}

function StatusPipeline({ session, retrying, retryError, onRetry, elapsed }: { session: SessionDetail; retrying: boolean; retryError: string | null; onRetry: () => void; elapsed: string }) {
  const steps: { status: ProcessingStatus; title: string }[] = [
    { status: "UPLOADED", title: "Received" },
    { status: "TRANSCRIBING", title: "Transcribing" },
    { status: "ANALYZING", title: "Finding themes" },
    { status: "COMPLETED", title: "Notes ready" },
  ];
  const failure = session.status === "FAILED";
  const order: ProcessingStatus[] = ["UPLOADED", "TRANSCRIBING", "ANALYZING", "COMPLETED"];
  const currentIndex = order.indexOf(session.status);
  return <section className={`pipeline-panel${failure ? " pipeline-failed" : ""}`}>
    <div className="pipeline-top"><div><span className="pipeline-title" role="status" aria-live="polite">{failure ? "Processing paused" : statusDescription(session.status).replace(/\.$/, "")}</span><span className="pipeline-subtitle">{failure ? `${session.failed_stage === "ANALYZING" ? "Your transcript is saved. " : "Your recording is saved. "}${friendlyFailure(session.safe_error_code)}` : session.status === "COMPLETED" ? "Your transcript and notes are saved." : `Working on this meeting · ${elapsed} elapsed`}</span></div>
      {failure && <button className="button button-secondary retry-button" onClick={onRetry} disabled={retrying}>{retrying ? <LoaderCircle size={15} className="spin" /> : <RefreshCw size={14} />}{retrying ? "Retrying" : "Retry processing"}</button>}
    </div>
    {failure && retryError && <p className="inline-error" role="alert">{retryError}</p>}
    {!failure && <ol className="pipeline-steps" aria-label={`Processing status: ${session.status.toLowerCase()}`}>
      {steps.map((step, index) => {
        const done = session.status === "COMPLETED" || index < currentIndex;
        const active = session.status !== "COMPLETED" && index === currentIndex;
        return <li key={step.status} className={`${done ? "step-done" : ""}${active ? " step-active" : ""}`}><span className="step-mark">{done ? <span className="step-check" /> : active ? <LoaderCircle size={13} className="spin" /> : <span className="step-ring" />}</span><span>{step.title}</span></li>;
      })}
    </ol>}
  </section>;
}

function SessionView({ session, loading, error, retrying, retryError, elapsed, onRetry, onRefresh, onCreateTask, onPatchTask }: {
  session: SessionDetail | null;
  loading: boolean;
  error: string | null;
  retrying: boolean;
  retryError: string | null;
  elapsed: string;
  onRetry: () => void;
  onRefresh: () => void;
  onCreateTask: (input: ActionItemInput) => Promise<void>;
  onPatchTask: (id: string, patch: Partial<ActionItem>) => Promise<void>;
}) {
  const [tab, setTab] = useState<ResultTab>("insights");
  useEffect(() => setTab("insights"), [session?.id]);
  if (loading && !session) return <div className="session-loading page-enter"><PageTitle title="Opening meeting" description="Loading your saved conversation…" /><div className="meeting-skeletons"><span /><span /><span /></div></div>;
  if (error && !session) return <div className="session-error-page page-enter"><PageTitle title="Meeting unavailable" description={error} /><button className="button button-secondary" onClick={onRefresh}><RefreshCw size={15} />Try again</button></div>;
  if (!session) return null;
  const isProcessing = session.status !== "COMPLETED" && session.status !== "FAILED";
  return <div className="session-view page-enter">
    <a className="back-link" href="?view=meetings" onClick={(event) => { event.preventDefault(); window.history.pushState(null, "", "?view=meetings"); window.dispatchEvent(new PopStateEvent("popstate")); }}><ArrowLeft size={14} />All meetings</a>
    <div className="session-title-row"><div className="session-title-copy"><h1>{session.title}</h1><p><CalendarDays size={13} />{formatDate(session.created_at, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}<span className="meta-dot">·</span><FileAudio2 size={13} /><span className="filename-text">{session.original_filename}</span><span className="meta-dot">·</span>{formatBytes(session.file_size_bytes)}</p></div><StatusBadge status={session.status} /></div>
    <StatusPipeline session={session} retrying={retrying} retryError={retryError} onRetry={onRetry} elapsed={elapsed} />
    {error && <div className="content-error session-network-error" role="status"><p>{error} The current results are still shown.</p><button className="text-action" onClick={onRefresh}>Refresh</button></div>}
    <div className="results-toolbar"><div className="result-tabs" aria-label="Meeting results">
      <button type="button" aria-pressed={tab === "insights"} className={`result-tab${tab === "insights" ? " result-tab-active" : ""}`} onClick={() => setTab("insights")}><Sparkles size={15} />AI insights<span>{session.topics.length}</span></button>
      <button type="button" aria-pressed={tab === "transcript"} className={`result-tab${tab === "transcript" ? " result-tab-active" : ""}`} onClick={() => setTab("transcript")}><AudioLines size={15} />Transcript<span>{session.transcript_segments.length}</span></button>
    </div><button className="icon-button refresh-detail" aria-label="Refresh meeting results" onClick={onRefresh}><RefreshCw size={14} /></button></div>
    {tab === "insights" ? <div className="insights-layout">
      <div className="insights-main"><TopicSummary topics={session.topics} status={session.status} /><ActionItems items={session.action_items} onCreate={onCreateTask} onPatch={onPatchTask} /></div>
      <aside className="insights-rail"><div className="rail-heading"><div><h2>Conversation</h2><p>Transcript preview</p></div><button className="text-action" onClick={() => setTab("transcript")}>Open <ArrowRight size={13} /></button></div>
        {session.transcript_segments.length ? <div className="transcript-preview">{session.transcript_segments.slice(0, 3).map((segment) => <article key={segment.id}><span>{segment.speaker_label || ""}{segment.start_ms !== null ? ` ${formatDuration(segment.start_ms)}` : ""}</span><p>{segment.text}</p></article>)}</div> : <div className="rail-empty"><AudioLines size={18} /><p>{session.failed_stage === "TRANSCRIBING" ? "The transcript could not be created yet." : isProcessing ? "Your transcript is being prepared." : "No transcript is available."}</p></div>}
      </aside>
    </div> : <section className="transcript-panel"><div className="section-heading"><div><h2>Transcript</h2><p>{session.transcript_segments.length ? `${session.transcript_segments.length} transcript segments` : "Conversation text"}</p></div></div><Transcript segments={session.transcript_segments} isProcessing={isProcessing} /></section>}
    <footer className="session-footer"><span><Clock3 size={13} />Saved {formatDate(session.updated_at, { hour: "numeric", minute: "2-digit", month: "short", day: "numeric" })}</span><span>Generated from the transcript. Edit any follow-up to make it yours.</span></footer>
  </div>;
}

function MeetingStudioPage({ recorder, file, setFile, title, setTitle, uploading, uploadError, onUpload, onBack }: {
  recorder: ReturnType<typeof useRecorder>;
  file: File | null;
  setFile: (file: File | null) => void;
  title: string;
  setTitle: (value: string) => void;
  uploading: boolean;
  uploadError: string | null;
  onUpload: () => void;
  onBack: () => void;
}) {
  return <div className="new-view page-enter"><button className="back-link" onClick={onBack}><ArrowLeft size={14} />Back to overview</button><div className="new-view-intro"><h1>New meeting</h1><p>Capture a conversation or add a recording to turn it into clear notes.</p></div><div className="studio-wrap"><RecordingStudio visible recorder={recorder} file={file} setFile={setFile} title={title} setTitle={setTitle} uploading={uploading} uploadError={uploadError} onUpload={onUpload} /></div><p className="new-view-note"><Headphones size={14} />Recording starts only when you choose Start recording. Audio is uploaded to your configured backend for processing.</p></div>;
}

export default function App() {
  const { route, navigate } = useRoute();
  const recorder = useRecorder();
  const [sessions, setSessions] = useState<SessionHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [recordingFile, setRecordingFile] = useState<File | null>(null);
  const [meetingTitle, setMeetingTitle] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [ageTick, setAgeTick] = useState(0);
  const [pollNonce, setPollNonce] = useState(0);
  const historyRequest = useRef(0);
  const PAGE_SIZE = 20;

  const refreshHistory = useCallback(async (nextOffset = 0, append = false) => {
    const requestId = ++historyRequest.current;
    setHistoryLoading(true);
    try {
      const result = await getSessions(nextOffset, PAGE_SIZE);
      if (requestId !== historyRequest.current) return;
      setSessions((current) => append ? [...current, ...result.items.filter((item) => !current.some((existing) => existing.id === item.id))] : result.items);
      setOffset(nextOffset);
      setTotal(result.total);
      setHistoryError(null);
    } catch (error) {
      if (requestId === historyRequest.current) setHistoryError(errorMessage(error));
    } finally {
      if (requestId === historyRequest.current) setHistoryLoading(false);
    }
  }, []);

  useEffect(() => { void refreshHistory(); }, [refreshHistory]);

  useEffect(() => {
    const onShortcut = (event: KeyboardEvent) => {
      const target = event.target;
      const editing = target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));
      if (!editing && !event.altKey && !event.ctrlKey && !event.metaKey && event.key.toLowerCase() === "n") {
        event.preventDefault();
        navigate({ view: "new" });
      }
    };
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, [navigate]);

  useEffect(() => {
    if (route.view !== "session" || !route.sessionId) { setSession(null); setSessionError(null); return; }
    let cancelled = false;
    let timer = 0;
    let attempt = 0;
    setSession(null);
    setSessionError(null);
    setSessionLoading(true);
    const poll = async () => {
      try {
        const latest = await getSession(route.sessionId!);
        if (cancelled) return;
        setSession(latest);
        setSessionError(null);
        setSessionLoading(false);
        attempt = 0;
        if (latest.status === "COMPLETED" || latest.status === "FAILED") {
          void refreshHistory();
          return;
        }
        const delays = [1600, 2300, 3400, 5000, 8000];
        timer = window.setTimeout(poll, delays[Math.min(attempt++, delays.length - 1)]);
      } catch (error) {
        if (cancelled) return;
        setSessionError(errorMessage(error));
        setSessionLoading(false);
        if (error instanceof ApiError && error.status === 404) return;
        timer = window.setTimeout(poll, Math.min(1500 * (2 ** Math.min(attempt++, 3)), 10000));
      }
    };
    void poll();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [route.view, route.sessionId, refreshHistory, pollNonce]);

  useEffect(() => {
    if (session?.status === "COMPLETED" || session?.status === "FAILED" || !session) return;
    const timer = window.setInterval(() => setAgeTick((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [session?.id, session?.status]);
  void ageTick;

  const handleLoadMore = () => { if (!historyLoading && offset + PAGE_SIZE < total) void refreshHistory(offset + PAGE_SIZE, true); };
  const handleUpload = async () => {
    if (uploading) return;
    const source = recordingFile || recorder.take;
    if (!source) { setUploadError("Choose a recording before uploading."); return; }
    const filename = recordingFile?.name || recorder.take?.filename || "meeting-recording.webm";
    const data = recordingFile || recorder.take?.blob;
    if (!data || !data.size) { setUploadError("This recording is empty. Choose or record another file."); return; }
    setUploading(true);
    setUploadError(null);
    try {
      const created = await uploadSession(data, filename, meetingTitle);
      setRecordingFile(null);
      recorder.discard();
      setMeetingTitle("");
      setUploading(false);
      void refreshHistory();
      navigate({ view: "session", sessionId: created.id });
    } catch (error) {
      setUploadError(errorMessage(error));
      setUploading(false);
    }
  };

  const handleRetry = async () => {
    if (!session || retrying || session.status !== "FAILED") return;
    setRetrying(true);
    setRetryError(null);
    try {
      await retrySession(session.id);
      setSession((current) => current ? { ...current, status: "UPLOADED", failed_stage: null, safe_error_code: null } : current);
      setPollNonce((value) => value + 1);
      void refreshHistory();
    } catch (error) { setRetryError(errorMessage(error)); }
    finally { setRetrying(false); }
  };

  const handleCreateTask = async (input: ActionItemInput) => {
    if (!session) return;
    const created = await addActionItem(session.id, input);
    setSession((current) => current ? { ...current, action_items: [...current.action_items, created] } : current);
  };

  const handlePatchTask = async (id: string, patch: Partial<ActionItem>) => {
    const updated = await updateActionItem(id, patch);
    setSession((current) => current ? { ...current, action_items: current.action_items.map((item) => item.id === id ? updated : item) } : current);
  };

  return <Shell route={route} historyItems={sessions} total={total} loadingHistory={historyLoading} historyError={historyError} onNavigate={navigate} onLoadMore={handleLoadMore} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} onRefreshHistory={() => void refreshHistory()}>
    {route.view === "home" && <HomeView sessions={sessions} total={total} loading={historyLoading} error={historyError} onNew={() => navigate({ view: "new" })} onMeetings={() => navigate({ view: "meetings" })} onOpen={(id) => navigate({ view: "session", sessionId: id })} onRetry={() => void refreshHistory()} />}
    {route.view === "meetings" && <LibraryView sessions={sessions} total={total} loading={historyLoading} error={historyError} offset={offset} pageSize={PAGE_SIZE} onOpen={(id) => navigate({ view: "session", sessionId: id })} onRetry={() => void refreshHistory()} onLoadMore={handleLoadMore} onNew={() => navigate({ view: "new" })} />}
    {route.view === "new" && <MeetingStudioPage recorder={recorder} file={recordingFile} setFile={(file) => { setRecordingFile(file); setUploadError(null); }} title={meetingTitle} setTitle={setMeetingTitle} uploading={uploading} uploadError={uploadError} onUpload={() => void handleUpload()} onBack={() => navigate({ view: "home" })} />}
    {route.view === "session" && <SessionView session={session} loading={sessionLoading} error={sessionError} retrying={retrying} retryError={retryError} elapsed={session ? processingAge(session.created_at) : "00:00:00"} onRetry={() => void handleRetry()} onRefresh={() => { if (route.sessionId) { setSessionLoading(true); setSessionError(null); void getSession(route.sessionId).then(setSession).catch((error) => setSessionError(errorMessage(error))).finally(() => setSessionLoading(false)); } }} onCreateTask={handleCreateTask} onPatchTask={handlePatchTask} />}
  </Shell>;
}
