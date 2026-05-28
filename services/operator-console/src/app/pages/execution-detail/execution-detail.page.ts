import { Component, DestroyRef, OnDestroy, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Subscription, forkJoin, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';
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
import { executionStatusModifier } from '../../core/ui/status-util';
import { workflowBadgeClass } from '../../core/ui/workflow-util';

const SECTION_LINKS = [
  { id: 'summary', label: 'Summary' },
  { id: 'lifecycle', label: 'Lifecycle' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'metrics', label: 'Metrics' },
  { id: 'replay', label: 'Replay' },
  { id: 'approval', label: 'Approval' },
] as const;

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
    @if (initialLoading) {
      <div class="oc-skeleton-stack" aria-busy="true">
        <div class="oc-skeleton oc-skeleton--ribbon"></div>
        <div class="oc-skeleton oc-skeleton--panel"></div>
      </div>
    } @else if (execution) {
      <header class="oc-exec-ribbon">
        <div class="oc-exec-ribbon__main">
          <h1 class="oc-exec-ribbon__title mono">{{ shortId(execution.execution_id) }}</h1>
          <span [class]="wfClass(execution.workflow_type)">{{ execution.workflow_type }}</span>
          <span class="status-badge {{ statusClass(execution.status) }}">{{ execution.status }}</span>
          @if (streamActive) {
            <span class="oc-live-pill" title="Subscribed to execution stream">Live</span>
          }
        </div>
        <p class="oc-exec-ribbon__id mono oc-meta">{{ execution.execution_id }}</p>
        <div class="oc-exec-ribbon__pills">
          @if (execution.parent_execution_id) {
            <span class="oc-pill">Replay child</span>
          }
          @if (execution.completed_at) {
            <span class="oc-pill oc-pill--muted">Completed {{ execution.completed_at }}</span>
          }
          @if (metrics?.total_latency_ms != null) {
            <span class="oc-pill oc-pill--muted">Latency {{ metrics!.total_latency_ms }} ms</span>
          }
        </div>
      </header>

      <nav class="oc-exec-nav" aria-label="Execution sections">
        @for (link of sectionLinks; track link.id) {
          <a class="oc-exec-nav__link" [href]="'#' + link.id">{{ link.label }}</a>
        }
      </nav>

      @if (streamError) {
        <p class="oc-meta oc-empty">Stream: {{ streamError }} (detail still refreshes on manual reload)</p>
      }

      <div class="oc-exec-layout">
        <div class="oc-exec-main oc-stack">
          <div id="summary">
            <app-execution-summary [execution]="execution" />
          </div>

          <section id="lifecycle" class="oc-panel">
            <h2 class="oc-section-title">Execution lifecycle</h2>
            <app-execution-steps [trace]="trace" />
          </section>

          <div id="timeline">
            <app-trace-timeline
              [trace]="trace"
              [loading]="loading"
              [error]="traceError"
              [totalLatencyMs]="metrics?.total_latency_ms ?? null"
              [newEventKeys]="newTimelineKeys"
            />
          </div>

          <div id="metrics">
            <app-execution-metrics
              [metrics]="metrics"
              [loading]="metricsLoading"
              [error]="metricsError"
            />
          </div>

          <div id="replay">
            <app-execution-replay-panel [execution]="execution" />
          </div>

          <div id="approval">
            <app-approval-panel [execution]="execution" (decided)="reload(false)" />
          </div>
        </div>
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
  initialLoading = true;
  loadError: string | null = null;
  streamActive = false;
  streamError: string | null = null;
  newTimelineKeys = new Set<string>();

  readonly sectionLinks = SECTION_LINKS;
  shortId = shortExecutionId;
  statusClass = executionStatusModifier;
  wfClass = workflowBadgeClass;

  private executionId = '';
  private streamAbort?: AbortController;
  private loadSub?: Subscription;

  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ExecutionApiService,
    private readonly metricsApi: MetricsApiService,
    private readonly stream: ExecutionStreamService,
  ) {}

  ngOnDestroy(): void {
    this.loadSub?.unsubscribe();
    this.stopStream();
  }

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        map((pm) => pm.get('executionId')),
        switchMap((id) => {
          if (!id) {
            this.loadError = 'Missing execution id';
            this.loading = false;
            this.initialLoading = false;
            return of(null);
          }
          this.executionId = id;
          return this.fetchExecutionBundle(id);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((bundle) => {
        if (!bundle) return;
        this.applyBundle(bundle);
      });
  }

  reload(hard = true): void {
    if (!this.executionId) return;
    this.loadSub?.unsubscribe();
    if (hard) {
      this.initialLoading = true;
      this.execution = null;
    }
    this.loadSub = this.fetchExecutionBundle(this.executionId).subscribe((bundle) => {
      if (bundle) this.applyBundle(bundle);
    });
  }

  private fetchExecutionBundle(executionId: string) {
    this.stopStream();
    this.newTimelineKeys.clear();
    this.streamError = null;
    this.loading = true;
    this.loadError = null;
    if (this.initialLoading) {
      this.metrics = null;
      this.metricsError = null;
      this.metricsLoading = false;
      this.traceError = null;
    }
    return forkJoin({
      ex: this.api.getExecution(executionId),
      tr: this.api.getTrace(executionId).pipe(
        catchError((e: Error) => of({ failed: true as const, message: e.message })),
      ),
    }).pipe(
      catchError((e: Error) => {
        this.loading = false;
        this.initialLoading = false;
        this.loadError = e.message;
        this.execution = null;
        this.trace = null;
        this.traceError = null;
        this.metrics = null;
        return of(null);
      }),
    );
  }

  private applyBundle({
    ex,
    tr,
  }: {
    ex: ExecutionDetail;
    tr: TraceView | { failed: true; message: string };
  }): void {
    this.execution = ex;
    if (tr && typeof tr === 'object' && 'failed' in tr && tr.failed) {
      this.trace = null;
      this.traceError = 'Could not load trace from api-gateway.';
    } else {
      this.trace = tr as TraceView;
      this.traceError = null;
    }
    this.loading = false;
    this.initialLoading = false;
    this.loadMetrics();
    this.maybeStartStream();
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
