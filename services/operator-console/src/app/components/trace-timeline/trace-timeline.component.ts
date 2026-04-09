import { JsonPipe } from '@angular/common';
import { Component, Input } from '@angular/core';
import type { TraceView } from '../../core/models/execution.models';
import { formatIsoShort } from '../../core/ui/format-util';
import {
  groupTimelineByStep,
  stepIdsInOrder,
  timelineEventKind,
  timelineEventSummary,
  type TimelineEvent,
  type TimelineGroup,
} from '../../core/ui/timeline-util';

@Component({
  selector: 'app-trace-timeline',
  standalone: true,
  imports: [JsonPipe],
  template: `
    <section class="oc-panel">
      <h2 class="oc-section-title">Trace timeline</h2>
      @if (!trace) {
        <p class="oc-meta oc-empty">No trace loaded for this execution.</p>
      } @else if (!trace.timeline.length) {
        <p class="oc-meta oc-empty">No timeline events recorded.</p>
      } @else {
        @for (g of groups; track g.key) {
          <div class="tl-group">
            <div class="tl-group__head">{{ g.label }}</div>
            @for (ev of g.events; track trackEv(ev, $index)) {
              <details class="tl-event {{ eventKind(ev) }}">
                <summary>
                  <span class="tl-event__ts oc-meta">{{ formatAt(ev['at']) }}</span>
                  <span class="tl-event__type">{{ str(ev['event_type']) }}</span>
                  <span class="tl-event__text">{{ summarize(ev) }}</span>
                </summary>
                <pre class="tl-payload oc-json">{{ ev | json }}</pre>
              </details>
            }
          </div>
        }

        <div class="tl-records">
          <details>
            <summary>
              Related records · tools {{ trace.tool_calls.length }} · policy {{ trace.policy_evaluations.length }}
              · approvals {{ trace.approvals.length }}
            </summary>
            @if (trace.tool_calls.length) {
              <div class="oc-label" style="margin: var(--space-3) 0 var(--space-2)">Tool calls</div>
              <pre class="oc-json">{{ trace.tool_calls | json }}</pre>
            }
            @if (trace.policy_evaluations.length) {
              <div class="oc-label" style="margin: var(--space-3) 0 var(--space-2)">Policy evaluations</div>
              <pre class="oc-json">{{ trace.policy_evaluations | json }}</pre>
            }
            @if (trace.approvals.length) {
              <div class="oc-label" style="margin: var(--space-3) 0 var(--space-2)">Approvals</div>
              <pre class="oc-json">{{ trace.approvals | json }}</pre>
            }
          </details>
        </div>
      }
    </section>
  `,
  styles: ``,
})
export class TraceTimelineComponent {
  @Input() trace: TraceView | null = null;

  str(v: unknown): string {
    if (v == null) return '';
    return String(v);
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

  trackEv(ev: TimelineEvent, i: number): string {
    return `${String(ev['at'])}-${String(ev['event_type'])}-${i}`;
  }

  get groups(): TimelineGroup[] {
    if (!this.trace?.timeline?.length) return [];
    return groupTimelineByStep(
      this.trace.timeline as TimelineEvent[],
      stepIdsInOrder(this.trace.steps),
    );
  }
}
