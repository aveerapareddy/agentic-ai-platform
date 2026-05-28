import { Component, Input } from '@angular/core';
import type { TraceView } from '../../core/models/execution.models';
import { formatIsoShort } from '../../core/ui/format-util';
import {
  buildTraceTimelineView,
  eventLatencyLabel,
  formatLatencyMs,
  type TraceStepGroupView,
} from '../../core/ui/trace-grouping-util';
import { hasPayloadDetails, payloadFieldRows } from '../../core/ui/trace-payload-util';
import {
  modelReasoningPathForStep,
  timelineEventKind,
  timelineEventSummary,
  type TimelineEvent,
} from '../../core/ui/timeline-util';

@Component({
  selector: 'app-trace-timeline',
  standalone: true,
  imports: [],
  template: `
    <section class="oc-panel">
      <h2 class="oc-section-title">Trace timeline</h2>
      <p class="oc-meta" style="margin: calc(-1 * var(--space-2)) 0 var(--space-4)">
        Events from trace projection and <span class="mono">GET …/stream</span> (SSE). Grouped for
        inspection only — no client-side semantics.
      </p>

      @if (loading) {
        <p class="oc-loading">Loading trace…</p>
      } @else if (error) {
        <div class="oc-error" role="alert">{{ error }}</div>
      } @else if (!trace) {
        <p class="oc-meta oc-empty">No trace loaded for this execution.</p>
      } @else if (!view.eventCount) {
        <p class="oc-meta oc-empty">No timeline events recorded.</p>
      } @else {
        @if (totalLatencyLabel) {
          <p class="oc-meta tl-exec-latency">
            <span class="oc-label">Total execution latency</span>
            {{ totalLatencyLabel }}
            <span class="tl-exec-latency__hint">(from evaluation metrics)</span>
          </p>
        }

        @for (group of view.groups; track group.key) {
          <div class="tl-step-group">
            <header class="tl-step-group__head">
              <div class="tl-step-group__title">
                @if (group.isExecutionLevel) {
                  <span class="tl-step-group__name">Execution</span>
                } @else {
                  <span class="tl-step-group__name">{{ group.label }}</span>
                  @if (group.stepId) {
                    <span class="mono oc-meta tl-step-group__id">{{ group.stepId }}</span>
                  }
                }
              </div>
              <div class="tl-step-group__meta">
                @if (group.stepStatus) {
                  <span class="status-badge status--neutral">{{ group.stepStatus }}</span>
                }
                @if (group.stepType) {
                  <span class="oc-meta">{{ group.stepType }}</span>
                }
                @if (group.durationMs != null) {
                  <span class="oc-meta tl-step-group__dur">{{ formatLatencyMs(group.durationMs) }}</span>
                }
                @if (!group.isExecutionLevel && modelPath(group)) {
                  <span
                    class="tl-path-badge"
                    [class.tl-path-badge--model]="modelPath(group) === 'model_runtime'"
                    [class.tl-path-badge--fb]="modelPath(group) === 'deterministic_fallback'"
                  >
                    {{ modelPathLabel(group) }}
                  </span>
                }
              </div>
              <div class="tl-step-group__counts oc-meta">
                @if (group.counts.model) {
                  <span>model {{ group.counts.model }}</span>
                }
                @if (group.counts.tool) {
                  <span>tool {{ group.counts.tool }}</span>
                }
                @if (group.counts.policy) {
                  <span>policy {{ group.counts.policy }}</span>
                }
                @if (group.counts.error) {
                  <span class="tl-count--err">error {{ group.counts.error }}</span>
                }
              </div>
            </header>

            @for (section of group.sections; track section.bucket) {
              <div class="tl-section">
                <div class="tl-section__label">{{ section.label }}</div>
                @for (ev of section.events; track trackEv(ev, $index)) {
                  <details class="tl-event {{ eventKind(ev) }}" [class.tl-event--live]="isLiveEvent(ev)">
                    <summary>
                      <span class="tl-event__ts oc-meta">{{ formatAt(ev['at']) }}</span>
                      <span class="tl-event__type">{{ eventTypeLabel(ev) }}</span>
                      <span class="tl-event__text">
                        {{ summarize(ev) }}
                        @if (eventLatency(ev)) {
                          <span class="tl-event__lat oc-meta"> · {{ eventLatency(ev) }}</span>
                        }
                      </span>
                    </summary>
                    @if (hasDetails(ev)) {
                      <div class="tl-event__body">
                        <dl class="tl-payload-dl">
                          @for (row of payloadRows(ev); track row.key) {
                            <dt>{{ row.key }}</dt>
                            <dd [class.mono]="row.multiline" [class.tl-payload-dl__pre]="row.multiline">
                              {{ row.value }}
                            </dd>
                          }
                        </dl>
                        <details class="tl-raw-json">
                          <summary class="oc-meta">Raw JSON</summary>
                          <pre class="tl-payload oc-json">{{ formatRawJson(ev) }}</pre>
                        </details>
                      </div>
                    } @else {
                      <p class="oc-meta tl-event__empty">No additional fields on this event.</p>
                    }
                  </details>
                }
              </div>
            }
          </div>
        }

        @if (hasRelatedRecords) {
          <div class="tl-records">
            <details>
              <summary>
                Related records · tools {{ trace.tool_calls.length }} · policy
                {{ trace.policy_evaluations.length }} · approvals {{ trace.approvals.length }}
              </summary>
              @if (trace.tool_calls.length) {
                <div class="oc-label" style="margin: var(--space-3) 0 var(--space-2)">Tool calls</div>
                @for (tc of trace.tool_calls; track toolTrack(tc, $index)) {
                  <details class="tl-record-card">
                    <summary>
                      <span class="mono">{{ str(tc['tool_name']) }}</span>
                      <span class="oc-meta"> · {{ str(tc['status']) }}</span>
                      @if (toolLatency(tc)) {
                        <span class="oc-meta"> · {{ toolLatency(tc) }}</span>
                      }
                    </summary>
                    <pre class="oc-json">{{ formatRawJson(tc) }}</pre>
                  </details>
                }
              }
              @if (trace.policy_evaluations.length) {
                <div class="oc-label" style="margin: var(--space-3) 0 var(--space-2)">Policy evaluations</div>
                <pre class="oc-json">{{ formatRawJson(trace.policy_evaluations) }}</pre>
              }
              @if (trace.approvals.length) {
                <div class="oc-label" style="margin: var(--space-3) 0 var(--space-2)">Approvals</div>
                <pre class="oc-json">{{ formatRawJson(trace.approvals) }}</pre>
              }
            </details>
          </div>
        }
      }
    </section>
  `,
  styles: `
    .tl-exec-latency {
      margin-bottom: var(--space-4);
    }
    .tl-exec-latency__hint {
      color: var(--muted);
      font-size: var(--text-meta);
    }
    .tl-step-group {
      margin-bottom: var(--space-6);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--surface);
      overflow: hidden;
    }
    .tl-step-group__head {
      padding: var(--space-3) var(--space-4);
      border-bottom: 1px solid var(--border);
      background: var(--bg);
    }
    .tl-step-group__title {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: var(--space-2);
      margin-bottom: var(--space-2);
    }
    .tl-step-group__name {
      font-weight: 600;
      font-size: var(--text-body);
    }
    .tl-step-group__id {
      font-size: var(--text-meta);
    }
    .tl-step-group__meta {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
      align-items: center;
      margin-bottom: var(--space-2);
    }
    .tl-step-group__dur {
      font-variant-numeric: tabular-nums;
    }
    .tl-step-group__counts {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
      font-size: var(--text-meta);
    }
    .tl-count--err {
      color: var(--err-muted);
    }
    .tl-path-badge {
      font-size: var(--text-meta);
      padding: 0.125rem 0.35rem;
      border-radius: 3px;
      border: 1px solid var(--border);
      color: var(--muted);
    }
    .tl-path-badge--model {
      border-color: rgba(76, 139, 245, 0.45);
      color: var(--accent-muted);
    }
    .tl-path-badge--fb {
      border-color: rgba(201, 162, 39, 0.45);
      color: var(--warn-text);
    }
    .tl-section {
      padding: var(--space-3) var(--space-4);
      border-bottom: 1px solid var(--border);
    }
    .tl-section:last-child {
      border-bottom: none;
    }
    .tl-section__label {
      font-size: var(--text-label);
      font-weight: 600;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: var(--space-3);
    }
    .tl-payload-dl {
      margin: 0;
      font-size: var(--text-meta);
      display: grid;
      grid-template-columns: minmax(6rem, 10rem) 1fr;
      gap: var(--space-1) var(--space-3);
    }
    .tl-payload-dl dt {
      color: var(--muted);
      margin: 0;
    }
    .tl-payload-dl dd {
      margin: 0;
      word-break: break-word;
    }
    .tl-payload-dl__pre {
      white-space: pre-wrap;
      font-size: 0.8125rem;
    }
    .tl-raw-json {
      margin-top: var(--space-3);
    }
    .tl-raw-json summary {
      cursor: pointer;
      font-size: var(--text-meta);
    }
    .tl-event__body {
      padding: 0 var(--space-4) var(--space-3);
    }
    .tl-event__lat {
      font-variant-numeric: tabular-nums;
    }
    .tl-event__empty {
      margin: 0;
      padding: 0 var(--space-4) var(--space-3);
    }
    .tl-event--live {
      border-left: 2px solid var(--accent);
    }
    .tl-record-card {
      border: 1px solid var(--border);
      border-radius: var(--radius);
      margin-bottom: var(--space-2);
      background: var(--bg);
    }
    .tl-record-card summary {
      padding: var(--space-2) var(--space-3);
      cursor: pointer;
      list-style: none;
    }
    .tl-record-card summary::-webkit-details-marker {
      display: none;
    }
    .tl-record-card pre {
      margin: 0;
      padding: var(--space-2) var(--space-3);
      border-top: 1px solid var(--border);
    }
  `,
})
export class TraceTimelineComponent {
  @Input() trace: TraceView | null = null;
  @Input() loading = false;
  @Input() error: string | null = null;
  @Input() totalLatencyMs: number | null = null;
  @Input() newEventKeys: Set<string> | null = null;

  formatLatencyMs = formatLatencyMs;
  payloadRows = payloadFieldRows;
  hasDetails = hasPayloadDetails;

  get view() {
    return buildTraceTimelineView(this.trace);
  }

  get totalLatencyLabel(): string | null {
    return formatLatencyMs(this.totalLatencyMs);
  }

  get hasRelatedRecords(): boolean {
    if (!this.trace) return false;
    return (
      this.trace.tool_calls.length > 0 ||
      this.trace.policy_evaluations.length > 0 ||
      this.trace.approvals.length > 0
    );
  }

  str(v: unknown): string {
    return v == null ? '' : String(v);
  }

  formatAt(v: unknown): string {
    return formatIsoShort(v == null ? '' : String(v));
  }

  summarize(ev: TimelineEvent): string {
    return timelineEventSummary(ev);
  }

  eventKind(ev: TimelineEvent): string {
    return timelineEventKind(String(ev['event_type'] ?? ''));
  }

  eventTypeLabel(ev: TimelineEvent): string {
    return String(ev['event_type'] ?? 'event');
  }

  eventLatency(ev: TimelineEvent): string | null {
    return eventLatencyLabel(ev);
  }

  trackEv(ev: TimelineEvent, i: number): string {
    const sk = ev['_streamKey'];
    if (typeof sk === 'string') return sk;
    return `${String(ev['at'])}-${String(ev['event_type'])}-${i}`;
  }

  isLiveEvent(ev: TimelineEvent): boolean {
    const sk = ev['_streamKey'];
    return typeof sk === 'string' && (this.newEventKeys?.has(sk) ?? false);
  }

  toolTrack(tc: Record<string, unknown>, i: number): string {
    return `${String(tc['tool_call_id'] ?? tc['tool_name'] ?? i)}`;
  }

  toolLatency(tc: Record<string, unknown>): string | null {
    const lat = tc['latency_ms'];
    if (typeof lat === 'number' && Number.isFinite(lat)) return formatLatencyMs(lat);
    return null;
  }

  formatRawJson(obj: unknown): string {
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  }

  modelPath(group: TraceStepGroupView): 'model_runtime' | 'deterministic_fallback' | null {
    if (!this.trace || !group.stepId) return null;
    return modelReasoningPathForStep(this.trace.timeline as TimelineEvent[], group.stepId);
  }

  modelPathLabel(group: TraceStepGroupView): string {
    const p = this.modelPath(group);
    if (p === 'model_runtime') return 'Model runtime';
    if (p === 'deterministic_fallback') return 'Deterministic fallback';
    return '';
  }
}
