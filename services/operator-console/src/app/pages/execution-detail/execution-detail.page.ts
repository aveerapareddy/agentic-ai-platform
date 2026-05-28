import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import { MetricsApiService } from '../../core/api/metrics-api.service';
import type { ExecutionDetail, TraceView } from '../../core/models/execution.models';
import type { ExecutionMetricsDto } from '../../core/models/metrics.models';
import { ExecutionSummaryComponent } from '../../components/execution-summary/execution-summary.component';
import { ExecutionStepsComponent } from '../../components/execution-steps/execution-steps.component';
import { TraceTimelineComponent } from '../../components/trace-timeline/trace-timeline.component';
import { ApprovalPanelComponent } from '../../components/approval-panel/approval-panel.component';
import { ExecutionMetricsComponent } from '../../components/execution-metrics/execution-metrics.component';
import { shortExecutionId } from '../../core/ui/format-util';

@Component({
  selector: 'app-execution-detail-page',
  standalone: true,
  imports: [
    RouterLink,
    ExecutionSummaryComponent,
    ApprovalPanelComponent,
    ExecutionMetricsComponent,
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
      <h1 class="oc-page-title mono">{{ shortId(execution.execution_id) }}</h1>
      <p class="oc-page-lead oc-meta mono" style="margin-top: calc(-1 * var(--space-2))">{{ execution.execution_id }}</p>

      <div class="oc-stack">
        <app-execution-summary [execution]="execution" />
        <app-approval-panel [execution]="execution" (decided)="reload()" />
        <app-execution-metrics
          [metrics]="metrics"
          [loading]="metricsLoading"
          [error]="metricsError"
        />
        <app-execution-steps [trace]="trace" />
        <app-trace-timeline [trace]="trace" />
      </div>
    }
  `,
  styles: ``,
})
export class ExecutionDetailPage implements OnInit {
  execution: ExecutionDetail | null = null;
  trace: TraceView | null = null;
  metrics: ExecutionMetricsDto | null = null;
  metricsLoading = false;
  metricsError: string | null = null;
  loading = true;
  loadError: string | null = null;

  shortId = shortExecutionId;

  private executionId = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ExecutionApiService,
    private readonly metricsApi: MetricsApiService,
  ) {}

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
    this.loading = true;
    this.loadError = null;
    this.metrics = null;
    this.metricsError = null;
    this.metricsLoading = false;
    forkJoin({
      ex: this.api.getExecution(this.executionId),
      tr: this.api.getTrace(this.executionId).pipe(catchError(() => of(null))),
    }).subscribe({
      next: ({ ex, tr }) => {
        this.execution = ex;
        this.trace = tr;
        this.loading = false;
        this.loadMetrics();
      },
      error: (e: Error) => {
        this.loading = false;
        this.loadError = e.message;
        this.execution = null;
        this.trace = null;
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
}
