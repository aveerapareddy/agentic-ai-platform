import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionDetail } from '../../core/models/execution.models';

@Component({
  selector: 'app-approval-panel',
  standalone: true,
  imports: [FormsModule],
  template: `
    @if (execution?.status === 'awaiting_approval') {
      <div class="panel approval">
        <h2>Approval</h2>
        <p class="muted">
          Execution is <strong>awaiting_approval</strong>. Decisions are sent to <code>/v1/executions/…/approvals</code>
          only; the platform applies governance rules.
        </p>
        <div class="row">
          <label>
            Approver
            <input type="text" [(ngModel)]="approver" name="approver" placeholder="e.g. operator_id" />
          </label>
        </div>
        <div class="row">
          <label>
            Notes
            <input type="text" [(ngModel)]="notes" name="notes" />
          </label>
        </div>
        <div class="actions">
          <button type="button" class="primary" [disabled]="!canSubmit" (click)="submit('approve')">
            Approve
          </button>
          <button type="button" class="danger" [disabled]="!canSubmit" (click)="submit('reject')">
            Reject
          </button>
        </div>
        @if (error) {
          <p class="err-text">{{ error }}</p>
        }
      </div>
    }
  `,
  styles: `
    .approval {
      border-color: var(--warn);
    }
    .row {
      margin-bottom: 0.65rem;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      color: var(--muted);
      font-size: 0.85rem;
    }
    input {
      max-width: 28rem;
    }
    .actions {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.75rem;
    }
    code {
      font-family: var(--mono);
      font-size: 0.85em;
    }
  `,
})
export class ApprovalPanelComponent {
  @Input() execution: ExecutionDetail | null = null;
  /** Emitted after a successful approval API call so the parent can reload execution + trace. */
  @Output() decided = new EventEmitter<void>();

  approver = '';
  notes = '';
  busy = false;
  error: string | null = null;

  constructor(private readonly api: ExecutionApiService) {}

  get canSubmit(): boolean {
    return !!this.approver.trim() && !this.busy && !!this.execution;
  }

  submit(decision: 'approve' | 'reject'): void {
    if (!this.execution) return;
    const gov = this.execution.result?.['governance'];
    if (!gov || typeof gov !== 'object') {
      this.error = 'Missing governance block on execution result; cannot submit approval.';
      return;
    }
    const g = gov as Record<string, unknown>;
    const action_proposal_id = g['proposal_id'] != null ? String(g['proposal_id']) : null;
    const policy_evaluation_id = g['evaluation_id'] != null ? String(g['evaluation_id']) : null;
    if (!action_proposal_id || !policy_evaluation_id) {
      this.error = 'Governance snapshot missing proposal_id or evaluation_id.';
      return;
    }
    this.busy = true;
    this.error = null;
    this.api
      .submitApproval(this.execution.execution_id, {
        action_proposal_id,
        policy_evaluation_id,
        decision,
        approver: this.approver.trim(),
        notes: this.notes.trim() || null,
      })
      .subscribe({
        next: () => {
          this.busy = false;
          this.decided.emit();
        },
        error: (e: Error) => {
          this.busy = false;
          this.error = e.message;
        },
      });
  }
}
