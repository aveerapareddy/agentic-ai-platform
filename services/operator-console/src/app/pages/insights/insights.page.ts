import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { InsightsApiService } from '../../core/api/insights-api.service';
import type { CrossExecutionInsightDto, MuktiInsightsSummaryDto } from '../../core/models/insights.models';
import { InsightCardComponent } from '../../components/insight-card/insight-card.component';
import { PageHeaderComponent } from '../../layout/page-header.component';

@Component({
  selector: 'app-insights-page',
  standalone: true,
  imports: [FormsModule, RouterLink, InsightCardComponent, PageHeaderComponent],
  template: `
    <app-page-header
      title="Mukti Insights"
      eyebrow="Intelligence"
      lead="Advisory rollups from GET /v1/insights/mukti. Derived server-side from execution_feedback — does not change live runs."
    />

    <div class="oc-filters">
      <label>
        Tenant ID
        <input type="text" [(ngModel)]="tenantId" name="tenant" />
      </label>
      <label>
        Workflow
        <input type="text" [(ngModel)]="workflowType" name="wf" placeholder="(any)" />
      </label>
      <label>
        Status
        <input type="text" [(ngModel)]="status" name="st" placeholder="(any)" />
      </label>
      <label>
        Limit
        <input type="number" [(ngModel)]="limit" name="lim" min="1" max="500" />
      </label>
      <button type="button" class="oc-btn" (click)="reload()" [disabled]="loading">Refresh</button>
    </div>

    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (initialLoading) {
      <div class="oc-skeleton-stack" aria-busy="true">
        <div class="oc-skeleton oc-skeleton--stat"></div>
        <div class="oc-skeleton oc-skeleton--panel"></div>
      </div>
    } @else if (summary && summary.execution_feedback_sample_size === 0) {
      <div class="oc-empty-state">
        <p class="oc-empty-state__title">No feedback in scope</p>
        <p class="oc-meta">{{ summary.scope_description }}</p>
        <a routerLink="/executions" class="oc-btn">Browse executions</a>
      </div>
    } @else if (summary) {
      <div class="oc-stat-row">
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Feedback sample</div>
          <div class="oc-stat-card__value">{{ summary.execution_feedback_sample_size }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Ranked suggestions</div>
          <div class="oc-stat-card__value">{{ summary.ranked_improvement_suggestions.length }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Failure insights</div>
          <div class="oc-stat-card__value">{{ summary.top_failure_types.length }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Unstable surfaces</div>
          <div class="oc-stat-card__value">{{ summary.unstable_workflows_or_steps.length }}</div>
        </div>
      </div>
      <p class="oc-meta oc-insights-scope">{{ summary.scope_description }}</p>

      @if (summary.ranked_improvement_suggestions.length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">Ranked recommendations</h2>
          <div class="oc-rank-list">
            @for (s of summary.ranked_improvement_suggestions; track s.rank) {
              <div class="oc-rank-item">
                <span class="oc-rank-item__n">{{ s.rank }}</span>
                <div class="oc-rank-item__body">
                  <div class="oc-rank-item__head">
                    <span class="mono oc-meta">{{ s.category }}</span>
                    <span class="oc-meta">evidence {{ s.evidence_count }}</span>
                  </div>
                  <p class="oc-rank-item__summary">{{ s.summary }}</p>
                  @if (s.suggested_action) {
                    <p class="oc-meta oc-rank-item__action">{{ s.suggested_action }}</p>
                  }
                  @if (s.affected_workflows.length) {
                    <div class="oc-insight-card__workflows">
                      @for (wf of s.affected_workflows; track wf) {
                        <span class="wf-badge">{{ wf }}</span>
                      }
                    </div>
                  }
                </div>
              </div>
            }
          </div>
        </section>
      }

      @if (allInsightCards.length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">Issue surfaces</h2>
          <div class="oc-insight-grid">
            @for (ins of allInsightCards; track ins.insight_id) {
              <app-insight-card [insight]="ins" />
            }
          </div>
        </section>
      }
    }
  `,
  styles: `
    .oc-insights-scope {
      margin-bottom: var(--space-5);
    }
    .oc-insight-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
      gap: var(--space-4);
    }
    .oc-rank-list {
      display: flex;
      flex-direction: column;
      gap: var(--space-3);
    }
    .oc-rank-item {
      display: grid;
      grid-template-columns: 2rem 1fr;
      gap: var(--space-3);
      padding: var(--space-3) var(--space-4);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--bg);
    }
    .oc-rank-item__n {
      font-size: var(--text-title);
      font-weight: 600;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }
    .oc-rank-item__head {
      display: flex;
      justify-content: space-between;
      gap: var(--space-2);
      margin-bottom: var(--space-1);
    }
    .oc-rank-item__summary {
      margin: 0;
      font-size: var(--text-body);
      color: var(--text);
    }
    .oc-rank-item__action {
      margin: var(--space-2) 0 0;
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
  initialLoading = true;
  loadError: string | null = null;

  constructor(private readonly insightsApi: InsightsApiService) {}

  get allInsightCards(): CrossExecutionInsightDto[] {
    if (!this.summary) return [];
    return [
      ...this.summary.top_failure_types,
      ...this.summary.recurring_patterns,
      ...this.summary.policy_friction_areas,
      ...this.summary.model_fallback_concentration,
      ...this.summary.unstable_workflows_or_steps,
    ];
  }

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
          this.initialLoading = false;
        },
        error: (e: Error) => {
          this.loading = false;
          this.initialLoading = false;
          this.loadError = e.message;
          this.summary = null;
        },
      });
  }
}
