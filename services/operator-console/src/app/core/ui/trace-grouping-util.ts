/**
 * UI-only trace presentation: group and sort gateway timeline rows for display.
 * Does not infer execution outcomes or compute platform semantics.
 */

import type { TraceStepRow, TraceView } from '../models/execution.models';
import {
  groupTimelineByStep,
  sortEventsByAt,
  stepIdsInOrder,
  type TimelineEvent,
  type TimelineGroup,
} from './timeline-util';

export type TraceEventBucket = 'execution' | 'model' | 'tool' | 'policy' | 'error';

export const TRACE_EVENT_BUCKET_ORDER: TraceEventBucket[] = [
  'execution',
  'model',
  'tool',
  'policy',
  'error',
];

export interface TraceEventSection {
  bucket: TraceEventBucket;
  label: string;
  events: TimelineEvent[];
}

export interface TraceStepGroupView {
  key: string;
  label: string;
  isExecutionLevel: boolean;
  stepId: string | null;
  stepStatus: string | null;
  stepType: string | null;
  durationMs: number | null;
  counts: Record<TraceEventBucket, number>;
  sections: TraceEventSection[];
}

export interface TraceTimelineViewModel {
  groups: TraceStepGroupView[];
  eventCount: number;
}

const BUCKET_LABELS: Record<TraceEventBucket, string> = {
  execution: 'Execution & steps',
  model: 'Model runtime',
  tool: 'Tools & retrieval',
  policy: 'Policy & approval',
  error: 'Errors & failures',
};

/** Classify a timeline row for presentation grouping only. */
export function classifyTraceEventBucket(ev: TimelineEvent): TraceEventBucket {
  if (isErrorLikeTimelineEvent(ev)) return 'error';
  const t = String(ev['event_type'] ?? '');
  switch (t) {
    case 'model_reasoning':
      return 'model';
    case 'tool_call_completed':
    case 'knowledge_retrieved':
      return 'tool';
    case 'policy_evaluated':
    case 'approval_required':
    case 'approval_received':
      return 'policy';
    default:
      return 'execution';
  }
}

/** Surface rows that already carry failure/denial signals from the gateway trace. */
export function isErrorLikeTimelineEvent(ev: TimelineEvent): boolean {
  const t = String(ev['event_type'] ?? '').toLowerCase();
  if (t.includes('fail') || t.includes('error')) return true;
  const status = String(ev['status'] ?? '').toLowerCase();
  if (status === 'failed' || status === 'error') return true;
  const path = String(ev['path'] ?? '').toLowerCase();
  if (path === 'policy_denied' || path.includes('denied')) return true;
  const outcome = String(ev['outcome'] ?? '').toLowerCase();
  if (outcome === 'failed' || outcome === 'denied') return true;
  const validation = String(ev['validation_status'] ?? '').toLowerCase();
  if (validation === 'failed') return true;
  if (ev['error_class'] != null || ev['error_message'] != null) return true;
  return false;
}

export function emptyTraceBucketCounts(): Record<TraceEventBucket, number> {
  return { execution: 0, model: 0, tool: 0, policy: 0, error: 0 };
}

export function countBuckets(events: TimelineEvent[]): Record<TraceEventBucket, number> {
  const counts = emptyTraceBucketCounts();
  for (const ev of events) {
    counts[classifyTraceEventBucket(ev)] += 1;
  }
  return counts;
}

export function sectionizeStepEvents(events: TimelineEvent[]): TraceEventSection[] {
  const sorted = sortEventsByAt(events);
  const buckets = new Map<TraceEventBucket, TimelineEvent[]>();
  for (const ev of sorted) {
    const b = classifyTraceEventBucket(ev);
    if (!buckets.has(b)) buckets.set(b, []);
    buckets.get(b)!.push(ev);
  }
  const sections: TraceEventSection[] = [];
  for (const bucket of TRACE_EVENT_BUCKET_ORDER) {
    const evs = buckets.get(bucket);
    if (!evs?.length) continue;
    sections.push({ bucket, label: BUCKET_LABELS[bucket], events: evs });
  }
  return sections;
}

function stepRowById(steps: TraceStepRow[], stepId: string): TraceStepRow | undefined {
  return steps.find((r) => String(r.step?.['step_id'] ?? '') === stepId);
}

function stepMetaFromRow(row: TraceStepRow | undefined): {
  stepStatus: string | null;
  stepType: string | null;
  durationMs: number | null;
} {
  if (!row) {
    return { stepStatus: null, stepType: null, durationMs: null };
  }
  const step = row.step;
  const sr = row.step_result;
  let durationMs: number | null = null;
  const lat = sr?.['latency_ms'];
  if (typeof lat === 'number' && Number.isFinite(lat)) durationMs = Math.round(lat);
  return {
    stepStatus: step?.['status'] != null ? String(step['status']) : null,
    stepType: step?.['step_type'] != null ? String(step['step_type']) : null,
    durationMs,
  };
}

function enrichGroup(g: TimelineGroup, steps: TraceStepRow[]): TraceStepGroupView {
  const isExecutionLevel = g.key === '__execution__';
  const stepId = isExecutionLevel ? null : g.key;
  const row = stepId ? stepRowById(steps, stepId) : undefined;
  const meta = stepMetaFromRow(row);
  const counts = countBuckets(g.events);
  return {
    key: g.key,
    label: g.label,
    isExecutionLevel,
    stepId,
    stepStatus: meta.stepStatus,
    stepType: meta.stepType,
    durationMs: meta.durationMs,
    counts,
    sections: sectionizeStepEvents(g.events),
  };
}

/** Build grouped trace view from gateway TraceView projection. */
export function buildTraceTimelineView(trace: TraceView | null): TraceTimelineViewModel {
  if (!trace?.timeline?.length) {
    return { groups: [], eventCount: 0 };
  }
  const timeline = trace.timeline as TimelineEvent[];
  const rawGroups = groupTimelineByStep(timeline, stepIdsInOrder(trace.steps));
  const groups = rawGroups.map((g) => enrichGroup(g, trace.steps));
  return { groups, eventCount: timeline.length };
}

export function formatLatencyMs(ms: number | null | undefined): string | null {
  if (ms == null || !Number.isFinite(ms)) return null;
  return `${Math.round(ms)} ms`;
}

export function eventLatencyLabel(ev: TimelineEvent): string | null {
  const lat = ev['latency_ms'];
  if (typeof lat === 'number' && Number.isFinite(lat)) return formatLatencyMs(lat);
  return null;
}
