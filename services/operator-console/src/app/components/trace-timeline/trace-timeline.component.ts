import { JsonPipe } from '@angular/common';
import { Component, Input } from '@angular/core';
import type { TraceView } from '../../core/models/execution.models';

@Component({
  selector: 'app-trace-timeline',
  standalone: true,
  imports: [JsonPipe],
  template: `
    <div class="panel">
      <h2>Trace</h2>
      @if (!trace) {
        <p class="muted">No trace loaded.</p>
      } @else {
        <h3>Timeline</h3>
        <ul class="events">
          @for (ev of trace.timeline; track $index) {
            <li>
              <span class="mono ts">{{ str(ev['at']) }}</span>
              <span class="et">{{ str(ev['event_type']) }}</span>
              @if (ev['path'] != null) {
                <span class="path mono">{{ str(ev['path']) }}</span>
              }
              @if (ev['event_type'] === 'model_reasoning') {
                <span class="hint">model / fallback path</span>
              }
            </li>
          }
        </ul>

        <h3>Steps</h3>
        <ul class="steps">
          @for (row of trace.steps; track $index) {
            <li>
              <span class="mono">{{ stepName(row) }}</span>
              <span class="badge">{{ str(row.step?.['status']) }}</span>
              <span class="muted type mono">{{ str(row.step?.['type']) }}</span>
              @if (row.step_result?.['validation_outcome']) {
                <span class="mono small">{{ str(row.step_result?.['validation_outcome']) }}</span>
              }
            </li>
          }
        </ul>

        <h3>Tool calls</h3>
        @if (trace.tool_calls.length === 0) {
          <p class="muted">None</p>
        } @else {
          <ul class="tools">
            @for (tc of trace.tool_calls; track $index) {
              <li class="mono small">
                {{ str(tc['tool_name']) }} · {{ str(tc['status']) }}
                @if (tc['latency_ms'] != null) {
                  · {{ str(tc['latency_ms']) }}ms
                }
              </li>
            }
          </ul>
        }

        <h3>Policy</h3>
        @if (trace.policy_evaluations.length === 0) {
          <p class="muted">None</p>
        } @else {
          <pre class="json-block">{{ trace.policy_evaluations | json }}</pre>
        }

        <h3>Approvals</h3>
        @if (trace.approvals.length === 0) {
          <p class="muted">None</p>
        } @else {
          <pre class="json-block">{{ trace.approvals | json }}</pre>
        }
      }
    </div>
  `,
  styles: `
    .muted {
      color: var(--muted);
    }
    .events,
    .steps,
    .tools {
      list-style: none;
      padding: 0;
      margin: 0 0 1rem;
    }
    .events li,
    .steps li {
      padding: 0.35rem 0;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      align-items: center;
    }
    .ts {
      color: var(--muted);
      min-width: 10rem;
    }
    .et {
      font-weight: 500;
    }
    .path {
      color: var(--accent);
    }
    .hint {
      font-size: 0.75rem;
      color: var(--muted);
    }
    .small {
      font-size: 0.8rem;
    }
    .type {
      color: var(--muted);
    }
    .json-block {
      margin: 0;
      padding: 0.75rem;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      overflow: auto;
      font-size: 0.78rem;
      font-family: var(--mono);
      max-height: 200px;
    }
  `,
})
export class TraceTimelineComponent {
  @Input() trace: TraceView | null = null;

  str(v: unknown): string {
    if (v == null) return '';
    return String(v);
  }

  stepName(row: { step?: Record<string, unknown> }): string {
    const input = row.step?.['input'];
    if (input && typeof input === 'object' && 'planner_step_name' in input) {
      return String((input as Record<string, unknown>)['planner_step_name']);
    }
    return String(row.step?.['step_id'] ?? '?');
  }
}
