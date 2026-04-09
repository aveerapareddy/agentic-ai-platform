import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionDetail, TraceView } from '../../core/models/execution.models';
import { ExecutionSummaryComponent } from '../../components/execution-summary/execution-summary.component';
import { ExecutionStepsComponent } from '../../components/execution-steps/execution-steps.component';
import { TraceTimelineComponent } from '../../components/trace-timeline/trace-timeline.component';
import { ApprovalPanelComponent } from '../../components/approval-panel/approval-panel.component';
import { shortExecutionId } from '../../core/ui/format-util';

@Component({
  selector: 'app-execution-detail-page',
  standalone: true,
  imports: [
    RouterLink,
    ExecutionSummaryComponent,
    ExecutionStepsComponent,
    ApprovalPanelComponent,
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
        <app-execution-steps [trace]="trace" />
        <app-approval-panel [execution]="execution" (decided)="reload()" />
        <app-trace-timeline [trace]="trace" />
      </div>
    }
  `,
  styles: ``,
})
export class ExecutionDetailPage implements OnInit {
  execution: ExecutionDetail | null = null;
  trace: TraceView | null = null;
  loading = true;
  loadError: string | null = null;

  shortId = shortExecutionId;

  private executionId = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ExecutionApiService,
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
    forkJoin({
      ex: this.api.getExecution(this.executionId),
      tr: this.api.getTrace(this.executionId).pipe(catchError(() => of(null))),
    }).subscribe({
      next: ({ ex, tr }) => {
        this.execution = ex;
        this.trace = tr;
        this.loading = false;
      },
      error: (e: Error) => {
        this.loading = false;
        this.loadError = e.message;
        this.execution = null;
        this.trace = null;
      },
    });
  }
}
