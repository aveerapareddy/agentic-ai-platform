import { JsonPipe } from '@angular/common';
import { Component, Input } from '@angular/core';
import type { ExecutionDetail } from '../../core/models/execution.models';

@Component({
  selector: 'app-execution-summary',
  standalone: true,
  imports: [JsonPipe],
  template: `
    @if (execution) {
      <div class="panel">
        <h2>Execution</h2>
        <dl class="grid">
          <dt>ID</dt>
          <dd class="mono">{{ execution.execution_id }}</dd>
          <dt>Workflow</dt>
          <dd>{{ execution.workflow_type }}</dd>
          <dt>Status</dt>
          <dd>
            <span class="badge" [class]="execution.status">{{ execution.status }}</span>
          </dd>
          <dt>Created</dt>
          <dd class="mono">{{ execution.created_at }}</dd>
          <dt>Updated</dt>
          <dd class="mono">{{ execution.updated_at }}</dd>
          @if (execution.completed_at) {
            <dt>Completed</dt>
            <dd class="mono">{{ execution.completed_at }}</dd>
          }
          @if (execution.parent_execution_id) {
            <dt>Parent</dt>
            <dd class="mono">{{ execution.parent_execution_id }}</dd>
          }
        </dl>
        @if (execution.result && summaryKeys.length) {
          <h3>Result summary</h3>
          <pre class="json-block">{{ pickResult() | json }}</pre>
        }
        @if (governance()) {
          <h3>Governance</h3>
          <pre class="json-block">{{ governance() | json }}</pre>
        }
        @if (execution.validation_summary) {
          <h3>Validation</h3>
          <pre class="json-block">{{ execution.validation_summary | json }}</pre>
        }
      </div>
    }
  `,
  styles: `
    .grid {
      display: grid;
      grid-template-columns: 8rem 1fr;
      gap: 0.35rem 1rem;
      margin: 0;
    }
    dt {
      color: var(--muted);
      margin: 0;
    }
    dd {
      margin: 0;
    }
    .json-block {
      margin: 0;
      padding: 0.75rem;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      overflow: auto;
      font-size: 0.8rem;
      font-family: var(--mono);
      max-height: 240px;
    }
  `,
})
export class ExecutionSummaryComponent {
  @Input() execution: ExecutionDetail | null = null;

  /** Surface a small subset of result for readability; full payload still in platform. */
  summaryKeys = ['outcome', 'workflow_type', 'approval_status', 'policy_decision', 'governance'];

  pickResult(): Record<string, unknown> {
    const r = this.execution?.result;
    if (!r) return {};
    const out: Record<string, unknown> = {};
    for (const k of this.summaryKeys) {
      if (k in r) out[k] = r[k];
    }
    if (Object.keys(out).length === 0) return r;
    return out;
  }

  governance(): Record<string, unknown> | null {
    const g = this.execution?.result?.['governance'];
    return g && typeof g === 'object' ? (g as Record<string, unknown>) : null;
  }
}
