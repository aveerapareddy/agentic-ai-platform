import { NgTemplateOutlet } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { InsightsApiService } from '../../core/api/insights-api.service';
import type { MuktiInsightsSummaryDto } from '../../core/models/insights.models';

@Component({
  selector: 'app-insights-page',
  standalone: true,
  imports: [FormsModule, RouterLink, NgTemplateOutlet],
  template: `
    <p class="back-link">
      <a routerLink="/executions">← Executions</a>
    </p>
    <h1 class="oc-page-title">Mukti cross-execution insights</h1>
    <p class="oc-page-lead">
      Advisory rollups from <span class="mono">GET /v1/insights/mukti</span>. Derived server-side from stored
      execution_feedback and execution projections; does not change live runs.
    </p>

    <div class="oc-filters">
      <label>
        Tenant ID
        <input type="text" [(ngModel)]="tenantId" (ngModelChange)="reload()" name="tenant" />
      </label>
      <label>
        Workflow
        <input type="text" [(ngModel)]="workflowType" (ngModelChange)="reload()" name="wf" placeholder="(any)" />
      </label>
      <label>
        Status
        <input type="text" [(ngModel)]="status" (ngModelChange)="reload()" name="st" placeholder="(any)" />
      </label>
      <label>
        Limit
        <input type="number" [(ngModel)]="limit" (ngModelChange)="reload()" name="lim" min="1" max="500" />
      </label>
      <button type="button" class="oc-btn" (click)="reload()" [disabled]="loading">Refresh</button>
    </div>

    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (loading) {
      <p class="oc-loading">Loading insights…</p>
    } @else if (summary && summary.execution_feedback_sample_size === 0) {
      <p class="oc-meta oc-empty">
        No execution_feedback rows in scope for these filters. Run post-execution Mukti analysis and refresh.
      </p>
      <p class="oc-meta">{{ summary.scope_description }}</p>
    } @else if (summary) {
      <div class="oc-stat-row">
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Feedback rows in scope</div>
          <div class="oc-stat-card__value">{{ summary.execution_feedback_sample_size }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Failure-type insights</div>
          <div class="oc-stat-card__value">{{ summary.top_failure_types.length }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Recurring patterns</div>
          <div class="oc-stat-card__value">{{ summary.recurring_patterns.length }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Ranked suggestions</div>
          <div class="oc-stat-card__value">{{ summary.ranked_improvement_suggestions.length }}</div>
        </div>
      </div>
      <p class="oc-meta" style="margin-bottom: var(--space-4)">{{ summary.scope_description }}</p>

      @if (summary.top_failure_types.length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">Top failure types</h2>
          <ng-container
            [ngTemplateOutlet]="insightTable"
            [ngTemplateOutletContext]="{ rows: summary.top_failure_types }"
          />
        </section>
      }

      @if (summary.recurring_patterns.length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">Recurring patterns</h2>
          <ng-container
            [ngTemplateOutlet]="insightTable"
            [ngTemplateOutletContext]="{ rows: summary.recurring_patterns }"
          />
        </section>
      }

      @if (summary.model_fallback_concentration.length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">Model fallback concentration</h2>
          <ng-container
            [ngTemplateOutlet]="insightTable"
            [ngTemplateOutletContext]="{ rows: summary.model_fallback_concentration }"
          />
        </section>
      }

      @if (summary.policy_friction_areas.length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">Policy friction areas</h2>
          <ng-container
            [ngTemplateOutlet]="insightTable"
            [ngTemplateOutletContext]="{ rows: summary.policy_friction_areas }"
          />
        </section>
      }

      @if (summary.unstable_workflows_or_steps.length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">Unstable workflows / steps</h2>
          <ng-container
            [ngTemplateOutlet]="insightTable"
            [ngTemplateOutletContext]="{ rows: summary.unstable_workflows_or_steps }"
          />
        </section>
      }

      @if (summary.ranked_improvement_suggestions.length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">Ranked improvement suggestions</h2>
          <div class="oc-table-wrap">
            <table class="oc-table oc-table--static">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Category</th>
                  <th>Summary</th>
                  <th>Evidence</th>
                  <th>Workflows</th>
                  <th>Suggested action</th>
                </tr>
              </thead>
              <tbody>
                @for (s of summary.ranked_improvement_suggestions; track s.rank) {
                  <tr>
                    <td>{{ s.rank }}</td>
                    <td class="mono">{{ s.category }}</td>
                    <td>{{ s.summary }}</td>
                    <td>{{ s.evidence_count }}</td>
                    <td class="oc-meta">{{ s.affected_workflows.join(', ') || '—' }}</td>
                    <td class="oc-meta">{{ s.suggested_action ?? '—' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }
    }

    <ng-template #insightTable let-rows="rows">
      <div class="oc-table-wrap">
        <table class="oc-table oc-table--static">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Title</th>
              <th>Evidence</th>
              <th>Workflows</th>
              <th>Description</th>
              <th>Suggested action</th>
            </tr>
          </thead>
          <tbody>
            @for (row of rows; track row.insight_id) {
              <tr>
                <td><span class="oc-severity oc-severity--{{ row.severity }}">{{ row.severity }}</span></td>
                <td class="mono">{{ row.title }}</td>
                <td>{{ row.evidence_count }}</td>
                <td class="oc-meta">{{ row.affected_workflows.join(', ') || '—' }}</td>
                <td class="oc-meta">{{ row.description }}</td>
                <td class="oc-meta">{{ row.suggested_action ?? '—' }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </ng-template>
  `,
  styles: `
    .oc-severity {
      text-transform: uppercase;
      font-size: var(--text-label);
      font-weight: 500;
    }
    .oc-severity--info {
      color: var(--muted);
    }
    .oc-severity--warning {
      color: var(--warn-text);
    }
    .oc-severity--elevated {
      color: var(--err-muted);
    }
  `,
})
export class InsightsPage implements OnInit {
  tenantId = '';
  workflowType = '';
  status = '';
  limit = 100;

  summary: MuktiInsightsSummaryDto | null = null;
  loading = false;
  loadError: string | null = null;

  constructor(private readonly insightsApi: InsightsApiService) {}

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.loadError = null;
    const lim = Math.min(500, Math.max(1, Number(this.limit) || 100));
    this.limit = lim;
    this.insightsApi
      .getMuktiInsights({
        tenant_id: this.tenantId.trim() || undefined,
        workflow_type: this.workflowType.trim() || undefined,
        status: this.status.trim() || undefined,
        limit: lim,
      })
      .subscribe({
        next: (res) => {
          this.summary = res;
          this.loading = false;
        },
        error: (e: Error) => {
          this.loading = false;
          this.loadError = e.message;
          this.summary = null;
        },
      });
  }
}
