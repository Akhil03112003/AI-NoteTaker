import { useState, type FormEvent } from "react";
import { Check, Circle, LoaderCircle, Plus } from "lucide-react";
import type { ActionItem, ActionItemInput, Priority } from "../types";

interface Props {
  items: ActionItem[];
  onCreate: (input: ActionItemInput) => Promise<void>;
  onPatch: (id: string, patch: Partial<ActionItem>) => Promise<void>;
}

interface Draft {
  description: string;
  assignee: string;
  due_date: string;
  timeframe: string;
  priority: Priority;
}

const blankDraft = (): Draft => ({ description: "", assignee: "Unassigned", due_date: "", timeframe: "", priority: "Medium" });

function dateLabel(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
}

function ActionForm({ initial, submitLabel, busy, onCancel, onSubmit }: {
  initial: Draft;
  submitLabel: string;
  busy: boolean;
  onCancel?: () => void;
  onSubmit: (draft: Draft) => Promise<void>;
}) {
  const [draft, setDraft] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const update = (key: keyof Draft, value: string) => setDraft((current) => ({ ...current, [key]: value }));
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.description.trim()) { setError("Add a task description before saving."); return; }
    setError(null);
    try { await onSubmit({ ...draft, description: draft.description.trim(), assignee: draft.assignee.trim() || "Unassigned" }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The task could not be saved. Try again."); }
  };

  return <form className="action-form" onSubmit={(event) => void submit(event)}>
    <label className="sr-only" htmlFor="task-description">Task description</label>
    <input className="text-field task-description" id="task-description" name="task-description" autoComplete="off" maxLength={1000} value={draft.description} onChange={(event) => update("description", event.target.value)} placeholder="Describe the next step…" />
    <div className="task-form-grid">
      <label className="form-field"><span>Assignee</span><input className="text-field" name="assignee" autoComplete="off" maxLength={200} value={draft.assignee} onChange={(event) => update("assignee", event.target.value)} placeholder="Unassigned" /></label>
      <label className="form-field"><span>Due date</span><input className="text-field" name="due-date" type="date" value={draft.due_date} onChange={(event) => update("due_date", event.target.value)} /></label>
      <label className="form-field"><span>Timeframe</span><input className="text-field" name="timeframe" maxLength={200} value={draft.timeframe} onChange={(event) => update("timeframe", event.target.value)} placeholder="Only if stated" /></label>
      <label className="form-field"><span>Priority</span><select className="text-field" name="priority" value={draft.priority} onChange={(event) => update("priority", event.target.value)}><option>High</option><option>Medium</option><option>Low</option></select></label>
    </div>
    {error && <p className="inline-error" role="alert">{error}</p>}
    <div className="form-actions"><button type="button" className="button button-quiet" onClick={onCancel} disabled={!onCancel || busy}>Cancel</button><button type="submit" className="button button-primary" disabled={busy}>{busy && <LoaderCircle className="spin" size={14} />}{submitLabel}</button></div>
  </form>;
}

export function ActionItems({ items, onCreate, onPatch }: Props) {
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [issue, setIssue] = useState<string | null>(null);
  const openCount = items.filter((item) => !item.is_completed).length;

  const saveNew = async (draft: Draft) => {
    setCreating(true);
    setIssue(null);
    try {
      await onCreate({ description: draft.description, assignee: draft.assignee || "Unassigned", due_date: draft.due_date || null, timeframe: draft.timeframe || null, priority: draft.priority });
      setAdding(false);
    } catch (error) { setIssue(error instanceof Error ? error.message : "The task could not be added."); }
    finally { setCreating(false); }
  };

  const saveEdit = async (item: ActionItem, draft: Draft) => {
    setBusyId(item.id);
    setIssue(null);
    try {
      await onPatch(item.id, { description: draft.description, assignee: draft.assignee || "Unassigned", due_date: draft.due_date || null, timeframe: draft.timeframe || null, priority: draft.priority });
      setEditingId(null);
    } catch (error) { setIssue(error instanceof Error ? error.message : "The task could not be updated."); }
    finally { setBusyId(null); }
  };

  const toggle = async (item: ActionItem) => {
    setBusyId(item.id);
    setIssue(null);
    try { await onPatch(item.id, { is_completed: !item.is_completed }); }
    catch (error) { setIssue(error instanceof Error ? error.message : "The task could not be updated."); }
    finally { setBusyId(null); }
  };

  return <section className="task-section" aria-labelledby="action-items-title">
    <div className="section-heading task-heading">
      <div><h2 id="action-items-title">Next steps</h2><p>{openCount} open{items.length ? ` of ${items.length}` : ""}</p></div>
      {!adding && <button className="text-action" onClick={() => { setAdding(true); setIssue(null); }}><Plus size={15} />Add task</button>}
    </div>
    {issue && <p className="inline-error" role="alert">{issue}</p>}
    {adding && <ActionForm initial={blankDraft()} submitLabel="Add task" busy={creating} onCancel={() => setAdding(false)} onSubmit={saveNew} />}
    {items.length === 0 && !adding ? <div className="task-empty"><p>No follow-ups yet.</p><button className="text-action" onClick={() => setAdding(true)}><Plus size={15} />Add the first task</button></div> :
      <ul className="action-list">{items.map((item) => {
        const due = dateLabel(item.due_date);
        const draft = { description: item.description, assignee: item.assignee, due_date: item.due_date || "", timeframe: item.timeframe || "", priority: item.priority };
        return <li key={item.id} className={`action-row${item.is_completed ? " action-done" : ""}`}>
          {editingId === item.id ? <ActionForm initial={draft} submitLabel="Save changes" busy={busyId === item.id} onCancel={() => setEditingId(null)} onSubmit={(next) => saveEdit(item, next)} /> : <>
            <button className={`task-check${item.is_completed ? " task-checked" : ""}`} aria-label={`${item.is_completed ? "Mark incomplete" : "Mark complete"}: ${item.description}`} aria-pressed={item.is_completed} disabled={busyId === item.id} onClick={() => void toggle(item)}>{busyId === item.id ? <LoaderCircle size={16} className="spin" /> : item.is_completed ? <Check size={14} /> : <Circle size={17} />}</button>
            <div className="action-content"><p className="action-description">{item.description}</p><div className="action-meta"><span>{item.assignee || "Unassigned"}</span>{due && <><span className="meta-dot">·</span><span>{due}</span></>}{item.timeframe && <><span className="meta-dot">·</span><span>{item.timeframe}</span></>}<span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span></div></div>
            <button className="text-action task-edit" onClick={() => { setEditingId(item.id); setAdding(false); }} aria-label={`Edit task: ${item.description}`}><span>Edit</span></button>
          </>}
        </li>;
      })}</ul>}
  </section>;
}
