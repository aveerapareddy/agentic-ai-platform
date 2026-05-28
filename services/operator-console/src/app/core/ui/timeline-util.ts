/** Group and summarize gateway trace timeline rows (orchestrator trace_timeline shape). */

export type TimelineEvent = Record<string, unknown>;

export interface TimelineGroup {
  key: string;
  label: string;
  events: TimelineEvent[];
}

export function sortEventsByAt(events: TimelineEvent[]): TimelineEvent[] {
  return [...events].sort((a, b) => String(a['at'] ?? '').localeCompare(String(b['at'] ?? '')));
}

export function stepIdsInOrder(stepRows: { step?: Record<string, unknown> }[]): string[] {
  const ids: string[] = [];
  for (const row of stepRows) {
    const sid = row.step?.['step_id'];
    if (sid != null && String(sid)) ids.push(String(sid));
  }
  return ids;
}

export function groupTimelineByStep(
  timeline: TimelineEvent[],
  stepOrder: string[],
): TimelineGroup[] {
  const sorted = sortEventsByAt(timeline);
  const execKey = '__execution__';
  const buckets = new Map<string, TimelineEvent[]>();

  for (const e of sorted) {
    const sidRaw = e['step_id'];
    const key =
      sidRaw == null || String(sidRaw).trim() === '' ? execKey : String(sidRaw);
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key)!.push(e);
  }

  const labelForStep = (sid: string, events: TimelineEvent[]): string => {
    const fromStep = events.find(
      (ev) =>
        ev['event_type'] === 'step_started' ||
        ev['event_type'] === 'step_completed' ||
        ev['event_type'] === 'model_reasoning',
    );
    const name = fromStep?.['planner_step_name'];
    if (name != null && String(name)) return String(name);
    return shortStepId(sid);
  };

  const groups: TimelineGroup[] = [];
  const execEvents = buckets.get(execKey);
  if (execEvents?.length) {
    groups.push({ key: execKey, label: 'Execution', events: execEvents });
  }

  const placed = new Set<string>(execEvents?.length ? [execKey] : []);
  for (const sid of stepOrder) {
    const evs = buckets.get(sid);
    if (!evs?.length) continue;
    groups.push({ key: sid, label: labelForStep(sid, evs), events: evs });
    placed.add(sid);
  }

  const extraKeys = [...buckets.keys()].filter((k) => !placed.has(k));
  extraKeys.sort((a, b) => {
    const ta = String(buckets.get(a)?.[0]?.['at'] ?? '');
    const tb = String(buckets.get(b)?.[0]?.['at'] ?? '');
    return ta.localeCompare(tb);
  });
  for (const sid of extraKeys) {
    const evs = buckets.get(sid)!;
    groups.push({ key: sid, label: labelForStep(sid, evs), events: evs });
  }
  return groups;
}

function shortStepId(sid: string): string {
  if (sid.length <= 14) return sid;
  return `${sid.slice(0, 8)}…`;
}

export function timelineEventKind(eventType: string): string {
  switch (eventType) {
    case 'step_started':
    case 'step_completed':
      return 'evt--step';
    case 'model_reasoning':
      return 'evt--model';
    case 'tool_call_completed':
      return 'evt--tool';
    case 'knowledge_retrieved':
      return 'evt--retrieval';
    case 'policy_evaluated':
      return 'evt--policy';
    case 'approval_required':
    case 'approval_received':
      return 'evt--approval';
    case 'validation_performed':
      return 'evt--validation';
    case 'replay_created':
      return 'evt--replay';
    case 'execution_status':
    case 'governed_outcome':
    case 'action_proposed':
      return 'evt--exec';
    default:
      if (eventType.toLowerCase().includes('fail') || eventType.toLowerCase().includes('error')) {
        return 'evt--error';
      }
      return 'evt--default';
  }
}

export function timelineEventSummary(ev: TimelineEvent): string {
  const t = String(ev['event_type'] ?? '');
  switch (t) {
    case 'step_started':
      return `Step started${planner(ev)}`;
    case 'step_completed':
      return `Step completed${planner(ev)}`;
    case 'model_reasoning': {
      const task = ev['task'] != null ? String(ev['task']) : '';
      const path = ev['path'] != null ? String(ev['path']) : '';
      return [task, path].filter(Boolean).join(' · ') || 'Model reasoning';
    }
    case 'tool_call_completed': {
      const name = ev['tool_name'] != null ? String(ev['tool_name']) : '';
      const st = ev['status'] != null ? String(ev['status']) : '';
      return [name, st].filter(Boolean).join(' · ') || 'Tool call';
    }
    case 'knowledge_retrieved': {
      const n = ev['chunk_count'];
      return n != null ? `Retrieval · ${n} chunk(s)` : 'Knowledge retrieved';
    }
    case 'policy_evaluated': {
      const d = ev['decision'] != null ? String(ev['decision']) : '';
      return d ? `Policy · ${d}` : 'Policy evaluated';
    }
    case 'approval_required':
      return 'Approval required';
    case 'approval_received': {
      const d = ev['decision'] != null ? String(ev['decision']) : '';
      return d ? `Approval recorded · ${d}` : 'Approval recorded';
    }
    case 'execution_status': {
      const s = ev['status'] != null ? String(ev['status']) : '';
      return s ? `Execution status · ${s}` : 'Execution status';
    }
    case 'action_proposed': {
      const a = ev['action_type'] != null ? String(ev['action_type']) : '';
      return a ? `Action proposed · ${a}` : 'Action proposed';
    }
    case 'governed_outcome': {
      const p = ev['path'] != null ? String(ev['path']) : '';
      return p ? `Governed outcome · ${p}` : 'Governed outcome';
    }
    case 'validation_performed': {
      const v = ev['validation_status'] != null ? String(ev['validation_status']) : '';
      return v ? `Validation · ${v}` : 'Validation performed';
    }
    case 'replay_created': {
      const mode = ev['replay_mode'] != null ? String(ev['replay_mode']) : '';
      const src = ev['source_execution_id'] != null ? String(ev['source_execution_id']) : '';
      return [mode ? `Replay · ${mode}` : 'Replay created', src ? `from ${src.slice(0, 8)}…` : '']
        .filter(Boolean)
        .join(' ');
    }
    default:
      return t || 'Event';
  }
}

function planner(ev: TimelineEvent): string {
  const n = ev['planner_step_name'];
  return n != null && String(n) ? ` · ${String(n)}` : '';
}

export function modelReasoningPathForStep(
  timeline: TimelineEvent[],
  stepId: string,
): 'model_runtime' | 'deterministic_fallback' | null {
  const hits = sortEventsByAt(timeline).filter(
    (e) => e['event_type'] === 'model_reasoning' && String(e['step_id'] ?? '') === stepId,
  );
  if (!hits.length) return null;
  const last = hits[hits.length - 1];
  const p = last['path'];
  if (p === 'model_runtime' || p === 'deterministic_fallback') return p;
  return null;
}
