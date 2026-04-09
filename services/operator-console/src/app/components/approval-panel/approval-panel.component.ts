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
      <section class="oc-panel approval-panel">
        <h2 class="approval-panel__title">Awaiting approval</h2>
        <p class="approval-panel__lead">
          This execution is gated on a human decision. Submitting sends
          <span class="mono">POST …/approvals</span>
          via api-gateway; the platform applies governance rules.
        </p>
        <div class="approval-panel__fields">
          <label>
            <span class="oc-label">Approver</span>
            <input type="text" [(ngModel)]="approver" name="approver" placeholder="Operator identity" />
          </label>
          <label>
            <span class="oc-label">Notes</span>
            <input type="text" [(ngModel)]="notes" name="notes" placeholder="Optional" />
          </label>
        </div>
        <div class="approval-panel__actions">
          <button type="button" class="oc-btn oc-btn--primary" [disabled]="!canSubmit" (click)="submit('approve')">
            @if (busy && lastIntent === 'approve') {
              Submitting…
            } @else {
              Approve
            }
          </button>
          <button type="button" class="oc-btn oc-btn--danger" [disabled]="!canSubmit" (click)="submit('reject')">
            @if (busy && lastIntent === 'reject') {
              Submitting…
            } @else {
              Reject
            }
          </button>
        </div>
        @if (error) {
          <p class="oc-err-text approval-panel__error">{{ error }}</p>
        }
      </section>
    }
  `,
  styles: `
    .mono {
      font-family: var(--mono);
      font-size: 0.9em;
    }
    .approval-panel__fields {
      display: flex;
      flex-direction: column;
      gap: var(--space-3);
      margin-top: var(--space-2);
    }
    .approval-panel__fields label {
      display: flex;
      flex-direction: column;
      gap: var(--space-1);
    }
    .approval-panel__fields input {
      max-width: 28rem;
    }
    .approval-panel__actions {
      display: flex;
      gap: var(--space-3);
      margin-top: var(--space-4);
      flex-wrap: wrap;
    }
    .approval-panel__error {
      margin-top: var(--space-3);
    }
  `,
})
export class ApprovalPanelComponent {
  @Input() execution: ExecutionDetail | null = null;
  @Output() decided = new EventEmitter<void>();

  approver = '';
  notes = '';
  busy = false;
  lastIntent: 'approve' | 'reject' | null = null;
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
    this.lastIntent = decision;
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
          this.lastIntent = null;
          this.decided.emit();
        },
        error: (e: Error) => {
          this.busy = false;
          this.lastIntent = null;
          this.error = e.message;
        },
      });
  }
}
