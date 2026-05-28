import { Component, Input, OnChanges } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ReplayApiService } from '../../core/api/replay-api.service';
import type { ExecutionDetail } from '../../core/models/execution.models';
import type { ReplayCreatedResponseDto, ReplayMode } from '../../core/models/replay.models';
import { REPLAY_PROVENANCE_INPUT_KEY } from '../../core/models/replay.constants';
import { shortExecutionId } from '../../core/ui/format-util';

@Component({
  selector: 'app-execution-replay-panel',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <section class="oc-panel">
      <h2 class="oc-section-title">Replay</h2>
      <p class="oc-meta" style="margin: calc(-1 * var(--space-2)) 0 var(--space-4)">
        Request a child execution via <span class="mono">POST /v1/executions/…/replay</span>. The platform
        creates a new run; the source execution is not modified.
      </p>

      @if (lineageParentId) {
        <div class="oc-meta" style="margin-bottom: var(--space-4)">
          <span class="oc-label">Lineage</span>
          Replay of
          <a [routerLink]="['/executions', lineageParentId]" class="mono">{{ shortId(lineageParentId) }}</a>
          @if (lineageMode) {
            <span> · mode {{ lineageMode }}</span>
          }
        </div>
      }

      <div class="oc-filters replay-form">
        <label>
          Mode
          <select [(ngModel)]="mode" name="replayMode" (ngModelChange)="onModeChange()">
            <option value="exact">exact</option>
            <option value="investigative">investigative</option>
          </select>
        </label>
        <label>
          Environment
          <input type="text" [(ngModel)]="environmentTarget" name="env" />
        </label>
        <label>
          Label
          <input type="text" [(ngModel)]="label" name="label" placeholder="Optional (required if no reason)" />
        </label>
        @if (mode === 'investigative') {
          <label>
            Reason
            <input
              type="text"
              [(ngModel)]="reason"
              name="reason"
              placeholder="Required if label empty"
            />
          </label>
          <label class="replay-form__wide">
            Input overrides (JSON object)
            <textarea
              [(ngModel)]="inputOverridesJson"
              name="overrides"
              rows="4"
              placeholder='{"severity": "low"}'
            ></textarea>
          </label>
        }
        <label class="replay-form__check">
          <input type="checkbox" [(ngModel)]="startExecution" name="start" />
          Start execution after create
        </label>
      </div>

      @if (overrideJsonError) {
        <div class="oc-error" role="alert">{{ overrideJsonError }}</div>
      }
      @if (submitError) {
        <div class="oc-error" role="alert">{{ submitError }}</div>
      }

      <button
        type="button"
        class="oc-btn oc-btn--primary"
        (click)="submit()"
        [disabled]="busy || !canSubmit"
      >
        @if (busy) {
          Requesting replay…
        } @else {
          Request replay
        }
      </button>

      @if (lastResult) {
        <div class="oc-panel replay-result" style="margin-top: var(--space-5)">
          <h3 class="oc-section-title">Replay created</h3>
          <dl class="oc-dl">
            <dt>Replay execution</dt>
            <dd class="mono">{{ lastResult.replay_execution_id }}</dd>
            <dt>Status</dt>
            <dd>{{ lastResult.status }}</dd>
            <dt>Mode</dt>
            <dd>{{ lastResult.replay_mode }}</dd>
          </dl>
          <p class="replay-result__actions">
            <a class="oc-btn" [routerLink]="['/executions', lastResult.replay_execution_id]">
              Open replay execution
            </a>
            <a
              class="oc-btn"
              [routerLink]="[
                '/executions',
                lastResult.source_execution_id,
                'replay-diff',
                lastResult.replay_execution_id,
              ]"
            >
              View replay diff
            </a>
          </p>
        </div>
      }
    </section>
  `,
  styles: `
    .replay-form {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
      gap: var(--space-3);
      margin-bottom: var(--space-4);
    }
    .replay-form__wide {
      grid-column: 1 / -1;
    }
    .replay-form__wide textarea {
      font-family: var(--mono);
      font-size: var(--text-body);
      width: 100%;
      max-width: 40rem;
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: var(--space-2);
    }
    .replay-form__check {
      display: flex;
      align-items: center;
      gap: var(--space-2);
    }
    .replay-result__actions {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
      margin: var(--space-4) 0 0;
    }
  `,
})
export class ExecutionReplayPanelComponent implements OnChanges {
  @Input() execution: ExecutionDetail | null = null;

  mode: ReplayMode = 'exact';
  environmentTarget = 'sandbox';
  label = '';
  reason = '';
  inputOverridesJson = '';
  startExecution = false;

  busy = false;
  overrideJsonError: string | null = null;
  submitError: string | null = null;
  lastResult: ReplayCreatedResponseDto | null = null;

  lineageParentId: string | null = null;
  lineageMode: ReplayMode | null = null;

  shortId = shortExecutionId;

  constructor(private readonly replayApi: ReplayApiService) {}

  ngOnChanges(): void {
    this.readLineage();
  }

  get canSubmit(): boolean {
    if (!this.execution || this.busy) return false;
    if (this.mode === 'investigative') {
      if (!this.reason.trim() && !this.label.trim()) return false;
      if (this.overrideJsonError) return false;
    }
    return Boolean(this.environmentTarget.trim());
  }

  onModeChange(): void {
    this.overrideJsonError = null;
    if (this.mode === 'exact') {
      this.inputOverridesJson = '';
      this.reason = '';
    }
  }

  submit(): void {
    if (!this.execution || !this.canSubmit) return;
    this.submitError = null;
    this.overrideJsonError = null;

    let inputOverrides: Record<string, unknown> | null = null;
    if (this.mode === 'investigative') {
      const raw = this.inputOverridesJson.trim();
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as unknown;
          if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
            this.overrideJsonError = 'Input overrides must be a JSON object (e.g. {"key": "value"}).';
            return;
          }
          inputOverrides = parsed as Record<string, unknown>;
        } catch {
          this.overrideJsonError = 'Invalid JSON in input overrides.';
          return;
        }
      }
    }

    this.busy = true;
    this.replayApi
      .requestReplay(this.execution.execution_id, {
        mode: this.mode,
        environment_target: this.environmentTarget.trim(),
        label: this.label.trim() || null,
        reason: this.reason.trim() || null,
        input_overrides: inputOverrides,
        start_execution: this.startExecution,
      })
      .subscribe({
        next: (res) => {
          this.busy = false;
          this.lastResult = res;
        },
        error: (e: Error) => {
          this.busy = false;
          this.submitError = e.message;
        },
      });
  }

  private readLineage(): void {
    this.lineageParentId = this.execution?.parent_execution_id ?? null;
    this.lineageMode = null;
    const prov = this.execution?.input?.[REPLAY_PROVENANCE_INPUT_KEY];
    if (prov && typeof prov === 'object' && !Array.isArray(prov)) {
      const p = prov as Record<string, unknown>;
      if (typeof p['source_execution_id'] === 'string') {
        this.lineageParentId = p['source_execution_id'];
      }
      const rm = p['replay_mode'];
      if (rm === 'exact' || rm === 'investigative') {
        this.lineageMode = rm;
      }
    }
  }
}
