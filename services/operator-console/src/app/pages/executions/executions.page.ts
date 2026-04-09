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
    <h1 class="oc-page-title">Executions</h1>
    <p class="oc-page-lead">
      List from <span class="mono">GET /v1/executions</span>. Filters use gateway query parameters; execution ID
      contains filter is applied to the loaded page client-side.
    </p>

    <div class="oc-filters">
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
        Execution ID contains
        <input type="text" [(ngModel)]="searchId" name="search" />
      </label>
      <button type="button" class="oc-btn" (click)="reload()" [disabled]="loading">Refresh</button>
    </div>

    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (loading) {
      <p class="oc-loading">Loading executions…</p>
    } @else {
      <app-execution-list [items]="filteredItems" (select)="open($event)" />
    }
  `,
  styles: ``,
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
