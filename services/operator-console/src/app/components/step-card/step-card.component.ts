import { JsonPipe } from '@angular/common';
import { Component, Input } from '@angular/core';
import type { TraceStepRow } from '../../core/models/execution.models';
import { stepStatusModifier } from '../../core/ui/status-util';

@Component({
  selector: 'app-step-card',
  standalone: true,
  imports: [JsonPipe],
  template: `
    @if (row) {
      <article class="step-card">
        <button type="button" class="step-card__header" (click)="expanded = !expanded" [attr.aria-expanded]="expanded">
          <div class="step-card__title-row">
            <span class="oc-data step-card__name">{{ stepName }}</span>
            <span class="status-badge {{ stepStatusClass }}">{{ stepStatusLabel }}</span>
            @if (durationLabel) {
              <span class="oc-meta step-card__duration">{{ durationLabel }}</span>
            }
            @if (pathLabel) {
              <span class="step-card__path" [class.step-card__path--model]="pathKind === 'model_runtime'" [class.step-card__path--fb]="pathKind === 'deterministic_fallback'">
                {{ pathLabel }}
              </span>
            }
          </div>
          <span class="oc-meta step-card__chev">{{ expanded ? '▼' : '▶' }}</span>
        </button>
        @if (expanded) {
          <div class="step-card__body">
            @if (hasInput) {
              <div class="step-card__block">
                <div class="oc-label">Input</div>
                <pre class="oc-json">{{ row.step?.['input'] | json }}</pre>
              </div>
            }
            @if (hasOutput) {
              <div class="step-card__block">
                <div class="oc-label">Output</div>
                <pre class="oc-json">{{ row.step_result?.['output'] | json }}</pre>
              </div>
            }
            @if (hasEvidence) {
              <div class="step-card__block">
                <div class="oc-label">Evidence</div>
                <pre class="oc-json">{{ row.step_result?.['evidence'] | json }}</pre>
              </div>
            }
            @if (hasErrors) {
              <div class="step-card__block">
                <div class="oc-label">Errors</div>
                <pre class="oc-json oc-json--err">{{ row.step_result?.['errors'] | json }}</pre>
              </div>
            }
            @if (!hasInput && !hasOutput && !hasEvidence && !hasErrors) {
              <p class="oc-meta">No step payload fields exposed for this row.</p>
            }
          </div>
        }
      </article>
    }
  `,
  styles: `
    .step-card {
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--surface);
      margin-bottom: var(--space-3);
    }
    .step-card__header {
      width: 100%;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: var(--space-3);
      padding: var(--space-3) var(--space-4);
      margin: 0;
      border: none;
      background: transparent;
      color: inherit;
      text-align: left;
      cursor: pointer;
      font: inherit;
    }
    .step-card__header:hover {
      background: var(--surface-hover);
    }
    .step-card__title-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--space-2) var(--space-3);
      min-width: 0;
    }
    .step-card__name {
      font-weight: 500;
    }
    .step-card__duration {
      font-variant-numeric: tabular-nums;
    }
    .step-card__path {
      font-size: var(--text-meta);
      padding: 0.125rem 0.35rem;
      border-radius: 3px;
      border: 1px solid var(--border);
      color: var(--muted);
    }
    .step-card__path--model {
      border-color: rgba(76, 139, 245, 0.45);
      color: var(--accent-muted);
    }
    .step-card__path--fb {
      border-color: rgba(201, 162, 39, 0.45);
      color: var(--warn-text);
    }
    .step-card__chev {
      flex-shrink: 0;
      opacity: 0.7;
    }
    .step-card__body {
      padding: 0 var(--space-4) var(--space-4);
      border-top: 1px solid var(--border);
    }
    .step-card__block {
      margin-top: var(--space-3);
    }
    .step-card__block:first-child {
      margin-top: var(--space-3);
    }
  `,
})
export class StepCardComponent {
  @Input({ required: true }) row!: TraceStepRow;
  /** From trace timeline `model_reasoning` for this step, if any. */
  @Input() pathKind: 'model_runtime' | 'deterministic_fallback' | null = null;

  expanded = false;

  get stepName(): string {
    const input = this.row.step?.['input'];
    if (input && typeof input === 'object' && 'planner_step_name' in input) {
      return String((input as Record<string, unknown>)['planner_step_name']);
    }
    return String(this.row.step?.['step_id'] ?? '?');
  }

  get stepStatusLabel(): string {
    return String(this.row.step?.['status'] ?? '—');
  }

  get stepStatusClass(): string {
    return stepStatusModifier(this.stepStatusLabel);
  }

  get durationLabel(): string | null {
    const ms = this.row.step_result?.['latency_ms'];
    if (typeof ms === 'number' && Number.isFinite(ms)) return `${Math.round(ms)} ms`;
    if (ms != null && ms !== '') return `${ms} ms`;
    return null;
  }

  get pathLabel(): string | null {
    if (this.pathKind === 'model_runtime') return 'Model runtime';
    if (this.pathKind === 'deterministic_fallback') return 'Deterministic fallback';
    if (this.pathKind === null) {
      const cd = this.row.step_result?.['confidence_detail'];
      if (cd && typeof cd === 'object' && 'source' in cd) {
        const src = String((cd as Record<string, unknown>)['source']);
        if (src.includes('model') || src === 'model_runtime') return 'Model runtime';
        if (src.includes('step_executor') || src.includes('fallback')) return 'Deterministic fallback';
      }
    }
    return null;
  }

  get hasInput(): boolean {
    const i = this.row.step?.['input'];
    return i != null && typeof i === 'object' && Object.keys(i as object).length > 0;
  }

  get hasOutput(): boolean {
    const o = this.row.step_result?.['output'];
    return o != null && typeof o === 'object' && Object.keys(o as object).length > 0;
  }

  get hasEvidence(): boolean {
    const e = this.row.step_result?.['evidence'];
    return Array.isArray(e) && e.length > 0;
  }

  get hasErrors(): boolean {
    const e = this.row.step_result?.['errors'];
    return Array.isArray(e) && e.length > 0;
  }
}
