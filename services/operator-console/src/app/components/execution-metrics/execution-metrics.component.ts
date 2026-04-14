import { Component, Input } from '@angular/core';
import type { ExecutionMetricsDto } from '../../core/models/metrics.models';

@Component({
  selector: 'app-execution-metrics',
  standalone: true,
  imports: [],
  template: `
    <section class="oc-panel">
      <h2 class="oc-section-title">Evaluation metrics</h2>
      <p class="oc-meta" style="margin: calc(-1 * var(--space-2)) 0 var(--space-4)">
        From <span class="mono">GET /v1/executions/…/metrics</span> (api-gateway). Values are computed server-side from
        stored trace and execution rows.
      </p>

      @if (loading) {
        <p class="oc-loading">Loading metrics…</p>
      } @else if (error) {
        <div class="oc-error" role="alert">{{ error }}</div>
      } @else if (!metrics) {
        <p class="oc-meta oc-empty">No metrics returned.</p>
      } @else {
        <dl class="oc-dl">
          <dt>Model fallback rate</dt>
          <dd>{{ formatRate(metrics.model_fallback_rate) }}</dd>
          <dt>Validation success</dt>
          <dd>{{ formatBool(metrics.validation_success) }}</dd>
          @if (metrics.validation_detail) {
            <dt>Validation basis</dt>
            <dd class="oc-meta">{{ metrics.validation_detail }}</dd>
          }
          <dt>Policy outcome</dt>
          <dd>{{ metrics.policy_outcome ?? '—' }}</dd>
          @if (metrics.policy_decisions.length) {
            <dt>Policy decisions (chronological)</dt>
            <dd>
              <ul class="oc-inline-list">
                @for (d of metrics.policy_decisions; track $index) {
                  <li class="mono">{{ d }}</li>
                }
              </ul>
            </dd>
          }
          <dt>Tool success rate</dt>
          <dd>{{ formatRate(metrics.tool_success_rate) }}</dd>
          <dt>Tool calls</dt>
          <dd class="oc-meta">{{ metrics.tool_calls_success }} / {{ metrics.tool_calls_total }} succeeded</dd>
          <dt>Total latency</dt>
          <dd>{{ formatLatency(metrics.total_latency_ms) }}</dd>
        </dl>

        @if (metrics.computation_notes.length) {
          <h3 class="oc-section-title" style="margin-top: var(--space-5)">Evaluation notes</h3>
          <p class="oc-meta" style="margin: calc(-1 * var(--space-2)) 0 var(--space-3)">
            Server-provided notes (thresholds, caveats, or signal text). Not computed in the browser.
          </p>
          <ul class="oc-notes-list">
            @for (n of metrics.computation_notes; track $index) {
              <li>{{ n }}</li>
            }
          </ul>
        }
      }
    </section>
  `,
  styles: `
    .oc-inline-list {
      margin: 0;
      padding-left: 1.25rem;
    }
    .oc-notes-list {
      margin: 0;
      padding-left: 1.25rem;
      color: var(--text);
      font-size: var(--text-body);
    }
    .oc-notes-list li {
      margin-bottom: var(--space-2);
    }
  `,
})
export class ExecutionMetricsComponent {
  @Input() metrics: ExecutionMetricsDto | null = null;
  @Input() loading = false;
  @Input() error: string | null = null;

  formatRate(v: number | null | undefined): string {
    if (v == null) return '—';
    return `${(v * 100).toFixed(1)}%`;
  }

  formatBool(v: boolean | null | undefined): string {
    if (v === true) return 'Yes';
    if (v === false) return 'No';
    return '—';
  }

  formatLatency(ms: number | null | undefined): string {
    if (ms == null) return '—';
    if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s (${ms} ms)`;
    return `${ms} ms`;
  }
}
