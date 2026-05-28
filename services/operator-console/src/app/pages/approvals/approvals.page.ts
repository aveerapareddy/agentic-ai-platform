import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionListItem } from '../../core/models/execution.models';
import { ExecutionListComponent } from '../../components/execution-list/execution-list.component';
import { PageHeaderComponent } from '../../layout/page-header.component';

@Component({
  selector: 'app-approvals-page',
  standalone: true,
  imports: [FormsModule, ExecutionListComponent, PageHeaderComponent],
  template: `
    <app-page-header
      title="Approvals"
      eyebrow="Governance"
      lead="Executions in awaiting_approval status from GET /v1/executions. Approve or reject on the execution detail page."
    />

    <div class="oc-filters">
      <label>
        Tenant ID
        <input type="text" [(ngModel)]="tenantId" (ngModelChange)="reload()" name="tenant" />
      </label>
      <button type="button" class="oc-btn" (click)="reload()" [disabled]="loading">Refresh</button>
    </div>

    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (loading) {
      <div class="oc-skeleton-stack" aria-busy="true">
        <div class="oc-skeleton oc-skeleton--table"></div>
      </div>
    } @else {
      <app-execution-list [items]="items" (select)="open($event)" />
    }
  `,
  styles: ``,
})
export class ApprovalsPage implements OnInit {
  tenantId = '';
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

  reload(): void {
    this.loading = true;
    this.loadError = null;
    this.api
      .listExecutions({
        tenant_id: this.tenantId.trim() || undefined,
        status: 'awaiting_approval',
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
