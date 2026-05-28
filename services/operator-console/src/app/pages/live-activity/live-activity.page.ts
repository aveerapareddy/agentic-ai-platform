import { Component, OnDestroy, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionListItem } from '../../core/models/execution.models';
import { isTerminalExecutionStatus } from '../../core/models/stream.models';
import { PageHeaderComponent } from '../../layout/page-header.component';
import { executionStatusModifier } from '../../core/ui/status-util';
import { formatIsoShort, shortExecutionId } from '../../core/ui/format-util';
import { workflowBadgeClass } from '../../core/ui/workflow-util';

const ACTIVE_STATUSES = new Set(['created', 'planning', 'executing', 'validating', 'awaiting_approval']);

@Component({
  selector: 'app-live-activity-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent],
  template: `
    <app-page-header
      title="Live Activity"
      eyebrow="Platform"
      lead="Non-terminal executions from GET /v1/executions. SSE subscriptions open per row when you drill into detail."
    />

    <div class="oc-live-toolbar">
      <span class="oc-live-pill" [class.oc-live-pill--off]="!polling">Live poll</span>
      <span class="oc-meta">Refresh every {{ pollSec }}s · {{ activeItems.length }} active</span>
      <button type="button" class="oc-btn" (click)="reload()" [disabled]="loading">Refresh now</button>
    </div>

    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (initialLoading) {
      <div class="oc-skeleton-stack" aria-busy="true">
        @for (i of [1, 2, 3]; track i) {
          <div class="oc-skeleton oc-skeleton--row"></div>
        }
      </div>
    } @else if (!activeItems.length) {
      <div class="oc-empty-state">
        <p class="oc-empty-state__title">No active executions</p>
        <p class="oc-meta">Terminal runs are hidden. Start a workflow via api-gateway or open the executions explorer.</p>
        <a routerLink="/executions" class="oc-btn oc-btn--primary">Browse executions</a>
      </div>
    } @else {
      <div class="oc-live-rail">
        @for (row of activeItems; track row.execution_id) {
          <a
            class="oc-live-card"
            [routerLink]="['/executions', row.execution_id]"
            [class.oc-live-card--approval]="row.status === 'awaiting_approval'"
          >
            <div class="oc-live-card__rail" aria-hidden="true"></div>
            <div class="oc-live-card__body">
              <div class="oc-live-card__top">
                <span class="mono oc-live-card__id">{{ shortId(row.execution_id) }}</span>
                <span [class]="workflowClass(row.workflow_type)">{{ row.workflow_type }}</span>
                <span class="status-badge {{ statusClass(row.status) }}">{{ row.status }}</span>
              </div>
              <p class="oc-meta oc-live-card__ts">Created {{ formatTs(row.created_at) }}</p>
              <span class="oc-live-card__hint oc-meta">Open for trace stream →</span>
            </div>
          </a>
        }
      </div>
    }
  `,
  styles: ``,
})
export class LiveActivityPage implements OnInit, OnDestroy {
  items: ExecutionListItem[] = [];
  loading = false;
  initialLoading = true;
  loadError: string | null = null;
  polling = true;
  pollSec = 8;
  private timer?: ReturnType<typeof setInterval>;

  shortId = shortExecutionId;
  formatTs = formatIsoShort;
  statusClass = executionStatusModifier;
  workflowClass = workflowBadgeClass;

  constructor(private readonly api: ExecutionApiService) {}

  get activeItems(): ExecutionListItem[] {
    return this.items.filter((i) => ACTIVE_STATUSES.has(i.status) || !isTerminalExecutionStatus(i.status));
  }

  ngOnInit(): void {
    this.reload();
    this.timer = setInterval(() => this.reload(), this.pollSec * 1000);
  }

  ngOnDestroy(): void {
    if (this.timer) clearInterval(this.timer);
  }

  reload(): void {
    this.loading = true;
    this.loadError = null;
    this.api.listExecutions({ limit: 200 }).subscribe({
      next: (res) => {
        this.items = res.items;
        this.loading = false;
        this.initialLoading = false;
      },
      error: (e: Error) => {
        this.loading = false;
        this.initialLoading = false;
        this.loadError = e.message;
      },
    });
  }
}
