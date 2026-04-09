import { Component, Input } from '@angular/core';
import type { TraceView } from '../../core/models/execution.models';
import { modelReasoningPathForStep } from '../../core/ui/timeline-util';
import { StepCardComponent } from '../step-card/step-card.component';

@Component({
  selector: 'app-execution-steps',
  standalone: true,
  imports: [StepCardComponent],
  template: `
    <section class="oc-panel">
      <h2 class="oc-section-title">Steps</h2>
      @if (!trace || trace.steps.length === 0) {
        <p class="oc-meta oc-empty">No steps in trace projection.</p>
      } @else {
        @for (row of trace.steps; track $index) {
          <app-step-card [row]="row" [pathKind]="pathForRow(row)" />
        }
      }
    </section>
  `,
  styles: `
    :host {
      display: block;
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
