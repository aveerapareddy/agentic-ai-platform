import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionDetail, TraceView } from '../../core/models/execution.models';
import { ExecutionSummaryComponent } from '../../components/execution-summary/execution-summary.component';
import { TraceTimelineComponent } from '../../components/trace-timeline/trace-timeline.component';
import { ApprovalPanelComponent } from '../../components/approval-panel/approval-panel.component';

@Component({
  selector: 'app-execution-detail-page',
  standalone: true,
  imports: [RouterLink, ExecutionSummaryComponent, TraceTimelineComponent, ApprovalPanelComponent],
  template: `
    <p class="back">
      <a routerLink="/executions">← Executions</a>
    </p>
    @if (loadError) {
      <p class="err-text">{{ loadError }}</p>
    }
    @if (loading) {
      <p class="muted">Loading…</p>
    } @else {
      <app-execution-summary [execution]="execution" />
      <app-approval-panel [execution]="execution" (decided)="reload()" />
      <app-trace-timeline [trace]="trace" />
    }
  `,
  styles: `
    .back {
      margin: 0 0 1rem;
    }
    .muted {
      color: var(--muted);
    }
  `,
})
export class ExecutionDetailPage implements OnInit {
  execution: ExecutionDetail | null = null;
  trace: TraceView | null = null;
  loading = true;
  loadError: string | null = null;

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
      tr: this.api.getTrace(this.executionId).pipe(
        catchError(() => of(null)),
      ),
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
