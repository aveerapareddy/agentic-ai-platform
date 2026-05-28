import { Component, OnDestroy, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription, finalize } from 'rxjs';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionListItem } from '../../core/models/execution.models';
import { withListLoadTimeout } from '../../core/ui/list-load.util';
import { ExecutionListComponent } from '../../components/execution-list/execution-list.component';
import { PageHeaderComponent } from '../../layout/page-header.component';

const WORKFLOWS = ['', 'incident_triage', 'cost_attribution', 'generic'];
const STATUSES = [
  '',
  'created',
  'planning',
  'executing',
  'validating',
  'awaiting_approval',
  'completed',
  'failed',
  'cancelled',
];

@Component({
  selector: 'app-executions-page',
  standalone: true,
  imports: [FormsModule, ExecutionListComponent, PageHeaderComponent],
  template: `
    <div class="oc-page-content">
      <app-page-header
        title="Executions"
        eyebrow="Platform"
        lead="List from GET /v1/executions. Gateway filters for tenant, workflow, and status; execution ID search is client-side on the loaded page."
      />

      <div class="oc-filters">
        <label>
          Tenant ID
          <input type="text" [(ngModel)]="tenantId" name="tenant" />
        </label>
        <label>
          Workflow
          <select [(ngModel)]="workflowType" (change)="reload()" name="wf">
            @for (w of workflows; track w) {
              <option [value]="w">{{ w || '(any)' }}</option>
            }
          </select>
        </label>
        <label>
          Status
          <select [(ngModel)]="status" (change)="reload()" name="st">
            @for (s of statuses; track s) {
              <option [value]="s">{{ s || '(any)' }}</option>
            }
          </select>
        </label>
        <label class="oc-filters__search">
          Execution ID contains
          <input
            type="search"
            [(ngModel)]="searchId"
            (ngModelChange)="applyClientFilter()"
            name="search"
            placeholder="Filter loaded rows…"
          />
        </label>
        <button type="button" class="oc-btn" (click)="reload()" [disabled]="loading">Refresh</button>
      </div>

      @if (loadError) {
        <div class="oc-error" role="alert">{{ loadError }}</div>
      }

      @if (initialLoading) {
        <div class="oc-skeleton-stack" aria-busy="true" aria-label="Loading executions">
          <div class="oc-skeleton oc-skeleton--table"></div>
        </div>
      } @else {
        <app-execution-list [items]="filteredItems" (select)="open($event)" />
        @if (!loading && !loadError && filteredItems.length === 0 && items.length === 0) {
          <p class="oc-meta oc-empty-hint">No executions returned. Run make docker-seed or start a workflow via api-gateway.</p>
        }
      }
    </div>
  `,
  styles: `
    .oc-page-content {
      display: block;
      min-height: 12rem;
    }
    .oc-filters__search {
      flex: 1 1 12rem;
      min-width: 10rem;
    }
    .oc-empty-hint {
      margin-top: var(--space-4);
    }
  `,
})
export class ExecutionsPage implements OnInit, OnDestroy {
  workflows = WORKFLOWS;
  statuses = STATUSES;

  tenantId = '';
  workflowType = '';
  status = '';
  searchId = '';

  items: ExecutionListItem[] = [];
  filteredItems: ExecutionListItem[] = [];
  loading = false;
  initialLoading = true;
  loadError: string | null = null;

  private loadSub?: Subscription;
  private readonly api = inject(ExecutionApiService);
  private readonly router = inject(Router);

  ngOnInit(): void {
    this.reload();
  }

  ngOnDestroy(): void {
    this.loadSub?.unsubscribe();
  }

  applyClientFilter(): void {
    const q = this.searchId.trim().toLowerCase();
    this.filteredItems = !q
      ? this.items
      : this.items.filter((i) => i.execution_id.toLowerCase().includes(q));
  }

  reload(): void {
    this.loadSub?.unsubscribe();
    this.loading = true;
    if (!this.items.length) {
      this.initialLoading = true;
    }
    this.loadError = null;

    this.loadSub = withListLoadTimeout(
      this.api.listExecutions({
        tenant_id: this.tenantId.trim() || undefined,
        workflow_type: this.workflowType || undefined,
        status: this.status || undefined,
        limit: 200,
      }),
    )
      .pipe(
        finalize(() => {
          this.loading = false;
          this.initialLoading = false;
        }),
      )
      .subscribe({
        next: (res) => {
          this.items = res.items ?? [];
          this.applyClientFilter();
        },
        error: (e: Error) => {
          this.loadError = e.message || 'Failed to load executions';
          this.items = [];
          this.filteredItems = [];
        },
      });
  }

  open(executionId: string): void {
    void this.router.navigate(['/executions', executionId]);
  }
}
