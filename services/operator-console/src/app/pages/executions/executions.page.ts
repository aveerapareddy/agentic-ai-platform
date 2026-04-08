import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionListItem } from '../../core/models/execution.models';
import { ExecutionListComponent } from '../../components/execution-list/execution-list.component';

const WORKFLOWS = ['', 'incident_triage', 'generic'];
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
  imports: [FormsModule, ExecutionListComponent],
  template: `
    <h1>Executions</h1>
    <p class="muted">
      Data from <code class="mono">GET /v1/executions</code>. Filters map to query params; execution ID search is client-side on the loaded page.
    </p>

    <div class="filters panel">
      <label>
        Tenant ID
        <input type="text" [(ngModel)]="tenantId" (ngModelChange)="reload()" name="tenant" />
      </label>
      <label>
        Workflow
        <select [(ngModel)]="workflowType" (ngModelChange)="reload()" name="wf">
          @for (w of workflows; track w) {
            <option [value]="w">{{ w || '(any)' }}</option>
          }
        </select>
      </label>
      <label>
        Status
        <select [(ngModel)]="status" (ngModelChange)="reload()" name="st">
          @for (s of statuses; track s) {
            <option [value]="s">{{ s || '(any)' }}</option>
          }
        </select>
      </label>
      <label>
        Search execution ID (contains)
        <input type="text" [(ngModel)]="searchId" name="search" />
      </label>
      <button type="button" (click)="reload()">Refresh</button>
    </div>

    @if (loadError) {
      <p class="err-text">{{ loadError }}</p>
    }
    @if (loading) {
      <p class="muted">Loading…</p>
    } @else {
      <app-execution-list [items]="filteredItems" (select)="open($event)" />
    }
  `,
  styles: `
    h1 {
      font-size: 1.35rem;
      margin: 0 0 0.5rem;
    }
    .muted {
      color: var(--muted);
      margin-bottom: 1rem;
    }
    .filters {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: flex-end;
      margin-bottom: 1rem;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      color: var(--muted);
      font-size: 0.85rem;
    }
  `,
})
export class ExecutionsPage implements OnInit {
  workflows = WORKFLOWS;
  statuses = STATUSES;

  tenantId = '';
  workflowType = '';
  status = '';
  searchId = '';

  items: ExecutionListItem[] = [];
  loading = false;
  loadError: string | null = null;

  constructor(
    private readonly api: ExecutionApiService,
    private readonly router: Router,
  ) {}

  ngOnInit(): void {
    this.reload();
  }

  get filteredItems(): ExecutionListItem[] {
    const q = this.searchId.trim().toLowerCase();
    if (!q) return this.items;
    return this.items.filter((i) => i.execution_id.toLowerCase().includes(q));
  }

  reload(): void {
    this.loading = true;
    this.loadError = null;
    this.api
      .listExecutions({
        tenant_id: this.tenantId.trim() || undefined,
        workflow_type: this.workflowType || undefined,
        status: this.status || undefined,
        limit: 200,
      })
      .subscribe({
        next: (res) => {
          this.items = res.items;
          this.loading = false;
        },
        error: (e: Error) => {
          this.loading = false;
          this.loadError = e.message;
          this.items = [];
        },
      });
  }

  open(executionId: string): void {
    void this.router.navigate(['/executions', executionId]);
  }
}
