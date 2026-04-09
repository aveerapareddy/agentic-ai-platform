import { JsonPipe } from '@angular/common';
import { Component, Input } from '@angular/core';
import type { ExecutionDetail } from '../../core/models/execution.models';
import { executionStatusModifier } from '../../core/ui/status-util';
import { formatIsoShort } from '../../core/ui/format-util';

@Component({
  selector: 'app-execution-summary',
  standalone: true,
  imports: [JsonPipe],
  template: `
    @if (execution) {
      <div class="oc-stack">
        <section class="oc-panel">
          <h2 class="oc-section-title">Summary</h2>
          <dl class="oc-dl">
            <dt>Execution</dt>
            <dd class="mono">{{ execution.execution_id }}</dd>
            <dt>Workflow</dt>
            <dd>{{ execution.workflow_type }}</dd>
            <dt>Status</dt>
            <dd>
              <span class="status-badge {{ statusClass(execution.status) }}">{{ execution.status }}</span>
            </dd>
            <dt>Created</dt>
            <dd>{{ formatTs(execution.created_at) }}</dd>
            <dt>Updated</dt>
            <dd>{{ formatTs(execution.updated_at) }}</dd>
            @if (execution.completed_at) {
              <dt>Completed</dt>
              <dd>{{ formatTs(execution.completed_at) }}</dd>
            }
            @if (execution.cancelled_at) {
              <dt>Cancelled</dt>
              <dd>{{ formatTs(execution.cancelled_at) }}</dd>
            }
            @if (execution.parent_execution_id) {
              <dt>Parent</dt>
              <dd class="mono">{{ execution.parent_execution_id }}</dd>
            }
          </dl>

          @if (execution.result && resultKeys.length) {
            <details class="oc-details">
              <summary>Final result (JSON)</summary>
              <pre class="oc-json">{{ execution.result | json }}</pre>
            </details>
          }

          @if (execution.validation_summary && keysOf(execution.validation_summary).length) {
            <details class="oc-details">
              <summary>Validation summary</summary>
              <pre class="oc-json">{{ execution.validation_summary | json }}</pre>
            </details>
          }
        </section>

        @if (showGovernance) {
          <section class="oc-panel">
            <h2 class="oc-section-title">Governance</h2>
            <dl class="oc-dl">
              @if (policyDecision) {
                <dt>Policy decision</dt>
                <dd>{{ policyDecision }}</dd>
              }
              @if (approvalState) {
                <dt>Approval state</dt>
                <dd>{{ approvalState }}</dd>
              }
              @if (proposedSummary) {
                <dt>Proposed action</dt>
                <dd class="mono">{{ proposedSummary }}</dd>
              }
              @if (govPhase) {
                <dt>Phase</dt>
                <dd>{{ govPhase }}</dd>
              }
              @if (proposalId) {
                <dt>Proposal</dt>
                <dd class="mono">{{ proposalId }}</dd>
              }
              @if (evaluationId) {
                <dt>Evaluation</dt>
                <dd class="mono">{{ evaluationId }}</dd>
              }
            </dl>
            @if (governanceExtraKeys.length) {
              <details class="oc-details">
                <summary>Governance snapshot (JSON)</summary>
                <pre class="oc-json">{{ governanceObject | json }}</pre>
              </details>
            }
          </section>
        }
      </div>
    }
  `,
  styles: ``,
})
export class ExecutionSummaryComponent {
  @Input() execution: ExecutionDetail | null = null;

  statusClass = executionStatusModifier;
  formatTs = formatIsoShort;

  keysOf(o: Record<string, unknown>): string[] {
    return Object.keys(o);
  }

  get resultKeys(): string[] {
    const r = this.execution?.result;
    if (!r || typeof r !== 'object') return [];
    return Object.keys(r);
  }

  get governanceObject(): Record<string, unknown> | null {
    const g = this.execution?.result?.['governance'];
    return g && typeof g === 'object' ? (g as Record<string, unknown>) : null;
  }

  get policyDecision(): string | null {
    const r = this.execution?.result;
    if (!r || typeof r !== 'object') return null;
    const top = r['policy_decision'];
    if (top != null) return String(top);
    const g = r['governance'];
    if (g && typeof g === 'object' && 'policy_decision' in g) {
      const v = (g as Record<string, unknown>)['policy_decision'];
      if (v != null) return String(v);
    }
    return null;
  }

  get approvalState(): string | null {
    const r = this.execution?.result;
    if (!r || typeof r !== 'object') return null;
    const v = r['approval_status'];
    return v != null ? String(v) : null;
  }

  get proposedSummary(): string | null {
    const r = this.execution?.result;
    if (!r || typeof r !== 'object') return null;
    const p = r['proposed_action'];
    if (!p || typeof p !== 'object') return null;
    const o = p as Record<string, unknown>;
    const t = o['type'] != null ? String(o['type']) : '';
    const id = o['proposal_id'] != null ? String(o['proposal_id']) : '';
    const bits = [t, id].filter(Boolean);
    return bits.length ? bits.join(' · ') : null;
  }

  get govPhase(): string | null {
    const g = this.governanceObject;
    const v = g?.['phase'];
    return v != null ? String(v) : null;
  }

  get proposalId(): string | null {
    const g = this.governanceObject;
    const v = g?.['proposal_id'];
    return v != null ? String(v) : null;
  }

  get evaluationId(): string | null {
    const g = this.governanceObject;
    const v = g?.['evaluation_id'];
    return v != null ? String(v) : null;
  }

  get showGovernance(): boolean {
    return !!(
      this.policyDecision ||
      this.approvalState ||
      this.proposedSummary ||
      this.govPhase ||
      this.proposalId ||
      this.evaluationId
    );
  }

  /** Keys in governance object not already shown as rows (for raw details). */
  get governanceExtraKeys(): string[] {
    const g = this.governanceObject;
    if (!g) return [];
    const shown = new Set(['phase', 'proposal_id', 'evaluation_id', 'policy_decision']);
    return Object.keys(g).filter((k) => !shown.has(k));
  }
}
