import { Component, Input } from '@angular/core';
import type { TraceView } from '../../core/models/execution.models';
import { modelReasoningPathForStep } from '../../core/ui/timeline-util';
import { StepCardComponent } from '../step-card/step-card.component';

@Component({
  selector: 'app-execution-steps',
  standalone: true,
  imports: [StepCardComponent],
  template: `
    @if (!trace || trace.steps.length === 0) {
      <p class="oc-meta oc-empty">No steps in trace projection.</p>
    } @else {
      <div class="oc-step-list">
        @for (row of trace.steps; track $index) {
          <app-step-card [row]="row" [pathKind]="pathForRow(row)" />
        }
      </div>
    }
  `,
  styles: `
    .oc-step-list {
      display: flex;
      flex-direction: column;
      gap: var(--space-3);
    }
  `,
})
export class ExecutionStepsComponent {
  @Input() trace: TraceView | null = null;

  pathForRow(row: { step?: Record<string, unknown> }): 'model_runtime' | 'deterministic_fallback' | null {
    if (!this.trace) return null;
    const sid = row.step?.['step_id'];
    if (sid == null) return null;
    return modelReasoningPathForStep(this.trace.timeline, String(sid));
  }
}
