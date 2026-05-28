import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import { ExecutionStreamService } from '../../core/api/execution-stream.service';
import { MetricsApiService } from '../../core/api/metrics-api.service';
import type { ExecutionDetail, TraceStepRow, TraceView } from '../../core/models/execution.models';
import type { ExecutionStreamEvent } from '../../core/models/stream.models';
import {
  isTerminalExecutionStatus,
  isTerminalStreamEvent,
} from '../../core/models/stream.models';
import type { ExecutionMetricsDto } from '../../core/models/metrics.models';
import { ExecutionSummaryComponent } from '../../components/execution-summary/execution-summary.component';
import { ExecutionStepsComponent } from '../../components/execution-steps/execution-steps.component';
import { TraceTimelineComponent } from '../../components/trace-timeline/trace-timeline.component';
import { ApprovalPanelComponent } from '../../components/approval-panel/approval-panel.component';
import { ExecutionMetricsComponent } from '../../components/execution-metrics/execution-metrics.component';
import { ExecutionReplayPanelComponent } from '../../components/execution-replay-panel/execution-replay-panel.component';
import { shortExecutionId } from '../../core/ui/format-util';

@Component({
  selector: 'app-execution-detail-page',
  standalone: true,
  imports: [
    RouterLink,
    ExecutionSummaryComponent,
    ApprovalPanelComponent,
    ExecutionMetricsComponent,
    ExecutionReplayPanelComponent,
    ExecutionStepsComponent,
    TraceTimelineComponent,
  ],
  template: `
    <p class="back-link">
      <a routerLink="/executions">← Executions</a>
    </p>
    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (loading) {
      <p class="oc-loading">Loading execution…</p>
    } @else if (execution) {
      <h1 class="oc-page-title mono">
        {{ shortId(execution.execution_id) }}
        @if (streamActive) {
          <span class="oc-live-badge" title="Subscribed to execution stream">Live</span>
        }
      </h1>
      <p class="oc-page-lead oc-meta mono" style="margin-top: calc(-1 * var(--space-2))">{{ execution.execution_id }}</p>
      @if (streamError) {
        <p class="oc-meta oc-empty">Stream: {{ streamError }} (detail still refreshes on manual reload)</p>
      }

      <div class="oc-stack">
        <app-execution-summary [execution]="execution" />
        <app-approval-panel [execution]="execution" (decided)="reload()" />
        <app-execution-metrics
          [metrics]="metrics"
          [loading]="metricsLoading"
          [error]="metricsError"
        />
        <app-execution-replay-panel [execution]="execution" />
        <app-execution-steps [trace]="trace" />
        <app-trace-timeline
          [trace]="trace"
          [loading]="loading"
          [error]="traceError"
          [totalLatencyMs]="metrics?.total_latency_ms ?? null"
          [newEventKeys]="newTimelineKeys"
        />
      </div>
    }
  `,
  styles: ``,
})
export class ExecutionDetailPage implements OnInit, OnDestroy {
  execution: ExecutionDetail | null = null;
  trace: TraceView | null = null;
  traceError: string | null = null;
  metrics: ExecutionMetricsDto | null = null;
  metricsLoading = false;
  metricsError: string | null = null;
  loading = true;
  loadError: string | null = null;
  streamActive = false;
  streamError: string | null = null;
  newTimelineKeys = new Set<string>();

  shortId = shortExecutionId;

  private executionId = '';
  private streamAbort?: AbortController;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ExecutionApiService,
    private readonly metricsApi: MetricsApiService,
    private readonly stream: ExecutionStreamService,
  ) {}

  ngOnDestroy(): void {
    this.stopStream();
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const id = pm.get('executionId');
      if (!id) {
        this.loadError = 'Missing execution id';
        this.loading = false;
        return;
      }
      this.executionId = id;
      this.reload();
    });
  }

  reload(): void {
    this.stopStream();
    this.newTimelineKeys.clear();
    this.streamError = null;
    this.loading = true;
    this.loadError = null;
    this.metrics = null;
    this.metricsError = null;
    this.metricsLoading = false;
    this.traceError = null;
    forkJoin({
      ex: this.api.getExecution(this.executionId),
      tr: this.api.getTrace(this.executionId).pipe(
        catchError((e: Error) => of({ failed: true as const, message: e.message })),
      ),
    }).subscribe({
      next: ({ ex, tr }) => {
        this.execution = ex;
        if (tr && typeof tr === 'object' && 'failed' in tr && tr.failed) {
          this.trace = null;
          this.traceError = 'Could not load trace from api-gateway.';
        } else {
          this.trace = tr as TraceView;
          this.traceError = null;
        }
        this.loading = false;
        this.loadMetrics();
        this.maybeStartStream();
      },
      error: (e: Error) => {
        this.loading = false;
        this.loadError = e.message;
        this.execution = null;
        this.trace = null;
        this.traceError = null;
        this.metrics = null;
      },
    });
  }

  private loadMetrics(): void {
    if (!this.executionId) return;
    this.metricsLoading = true;
    this.metricsError = null;
    this.metricsApi.getExecutionMetrics(this.executionId).subscribe({
      next: (mx) => {
        this.metrics = mx;
        this.metricsLoading = false;
      },
      error: () => {
        this.metricsLoading = false;
        this.metricsError = 'Could not load evaluation metrics from api-gateway.';
        this.metrics = null;
      },
    });
  }

  private maybeStartStream(): void {
    if (!this.execution || isTerminalExecutionStatus(this.execution.status)) {
      return;
    }
    this.streamAbort = this.stream.connect(this.executionId, {
      onEvent: (ev) => this.applyStreamEvent(ev),
      onError: (msg) => {
        this.streamError = msg;
        this.streamActive = false;
      },
      onClose: () => {
        this.streamActive = false;
      },
    });
    this.streamActive = true;
  }

  private stopStream(): void {
    this.streamAbort?.abort();
    this.streamAbort = undefined;
    this.streamActive = false;
  }

  private applyStreamEvent(ev: ExecutionStreamEvent): void {
    if (ev.event_type === 'heartbeat') return;

    if (this.execution && ev.event_type === 'execution_updated') {
      const st = ev.payload['status'];
      if (typeof st === 'string') {
        this.execution = { ...this.execution, status: st };
      }
    }

    if (ev.event_type === 'approval_required' && this.execution) {
      this.execution = { ...this.execution, status: 'awaiting_approval' };
    }

    if (ev.event_type === 'trace_event' && this.trace) {
      const p = ev.payload;
      const row: Record<string, unknown> = {
        event_type: p['event_type'] ?? 'trace_event',
        at: p['at'] ?? ev.emitted_at,
        _streamKey: `seq-${ev.sequence}`,
      };
      const detail = p['detail'];
      if (detail && typeof detail === 'object') {
        Object.assign(row, detail as Record<string, unknown>);
      }
      this.trace = {
        ...this.trace,
        timeline: [...this.trace.timeline, row],
      };
      this.newTimelineKeys = new Set(this.newTimelineKeys).add(`seq-${ev.sequence}`);
    }

    if (ev.event_type === 'step_updated' && this.trace) {
      const stepId = String(ev.payload['step_id'] ?? '');
      const steps = this.trace.steps.map((row: TraceStepRow) => {
        const s = row.step;
        if (!s || String(s['step_id']) !== stepId) return row;
        return {
          ...row,
          step: { ...s, status: ev.payload['status'] ?? s['status'] },
        };
      });
      this.trace = { ...this.trace, steps };
    }

    if (
      ev.event_type === 'execution_completed' ||
      ev.event_type === 'execution_failed' ||
      ev.event_type === 'execution_cancelled'
    ) {
      const st = String(ev.payload['status'] ?? ev.event_type.replace('execution_', ''));
      if (this.execution) {
        this.execution = { ...this.execution, status: st };
      }
      this.stopStream();
      void this.api.getExecution(this.executionId).subscribe({
        next: (ex) => {
          this.execution = ex;
        },
      });
    }

    if (isTerminalStreamEvent(ev.event_type)) {
      this.stopStream();
    }
  }
}
