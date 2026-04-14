import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MetricsApiService } from '../../core/api/metrics-api.service';
import type { AggregatedMetricsDto } from '../../core/models/metrics.models';

@Component({
  selector: 'app-metrics-page',
  standalone: true,
  imports: [FormsModule, RouterLink],
  template: `
    <p class="back-link">
      <a routerLink="/executions">← Executions</a>
    </p>
    <h1 class="oc-page-title">Platform metrics</h1>
    <p class="oc-page-lead">
      Aggregates from <span class="mono">GET /v1/metrics</span>. Dimensions match evaluation-engine rollups; no client-side
      recomputation.
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
      <p class="oc-loading">Loading aggregates…</p>
    } @else if (aggregated && aggregated.executions_in_scope === 0) {
      <p class="oc-meta oc-empty">No executions in scope for these filters. Adjust tenant or limits and refresh.</p>
    } @else if (aggregated) {
      <div class="oc-stat-row">
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Executions in scope</div>
          <div class="oc-stat-card__value">{{ aggregated.executions_in_scope }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Workflow types</div>
          <div class="oc-stat-card__value">{{ sortedKeys(aggregated.by_workflow_type).length }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Step types</div>
          <div class="oc-stat-card__value">{{ sortedKeys(aggregated.by_step_type).length }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Tools</div>
          <div class="oc-stat-card__value">{{ sortedKeys(aggregated.by_tool_name).length }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Policy decisions</div>
          <div class="oc-stat-card__value">{{ sortedKeys(aggregated.by_policy_decision).length }}</div>
        </div>
      </div>

      @if (sortedKeys(aggregated.by_workflow_type).length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">By workflow type</h2>
          <div class="oc-table-wrap">
            <table class="oc-table oc-table--static">
              <thead>
                <tr>
                  <th>Workflow</th>
                  <th>Executions</th>
                  <th>Failed</th>
                  <th>Mean fallback</th>
                  <th>Mean tool success</th>
                </tr>
              </thead>
              <tbody>
                @for (wf of sortedKeys(aggregated.by_workflow_type); track wf) {
                  <tr>
                    <td class="mono">{{ wf }}</td>
                    <td>{{ aggregated.by_workflow_type[wf].execution_count }}</td>
                    <td>{{ aggregated.by_workflow_type[wf].failed_execution_count }}</td>
                    <td>{{ pct(aggregated.by_workflow_type[wf].mean_model_fallback_rate) }}</td>
                    <td>{{ pct(aggregated.by_workflow_type[wf].mean_tool_success_rate) }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          @if (policyRowsForWorkflow().length) {
            <p class="oc-meta" style="margin: var(--space-3) 0 var(--space-2)">Policy decision counts (per workflow)</p>
            <div class="oc-table-wrap">
              <table class="oc-table oc-table--static">
                <thead>
                  <tr>
                    <th>Workflow</th>
                    <th>Decision</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  @for (row of policyRowsForWorkflow(); track row.key) {
                    <tr>
                      <td class="mono">{{ row.workflow }}</td>
                      <td>{{ row.decision }}</td>
                      <td>{{ row.count }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </section>
      }

      @if (sortedKeys(aggregated.by_step_type).length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">By step type</h2>
          <div class="oc-table-wrap">
            <table class="oc-table oc-table--static">
              <thead>
                <tr>
                  <th>Step type</th>
                  <th>Steps</th>
                  <th>Succeeded</th>
                  <th>Failed</th>
                  <th>Model events</th>
                  <th>Fallback events</th>
                </tr>
              </thead>
              <tbody>
                @for (st of sortedKeys(aggregated.by_step_type); track st) {
                  <tr>
                    <td class="mono">{{ st }}</td>
                    <td>{{ aggregated.by_step_type[st].step_count }}</td>
                    <td>{{ aggregated.by_step_type[st].succeeded }}</td>
                    <td>{{ aggregated.by_step_type[st].failed }}</td>
                    <td>{{ aggregated.by_step_type[st].model_reasoning_events }}</td>
                    <td>{{ aggregated.by_step_type[st].model_fallback_events }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }

      @if (sortedKeys(aggregated.by_tool_name).length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">By tool name</h2>
          <div class="oc-table-wrap">
            <table class="oc-table oc-table--static">
              <thead>
                <tr>
                  <th>Tool</th>
                  <th>Invocations</th>
                  <th>Successes</th>
                  <th>Failures</th>
                </tr>
              </thead>
              <tbody>
                @for (tn of sortedKeys(aggregated.by_tool_name); track tn) {
                  <tr>
                    <td class="mono">{{ tn }}</td>
                    <td>{{ aggregated.by_tool_name[tn].invocations }}</td>
                    <td>{{ aggregated.by_tool_name[tn].successes }}</td>
                    <td>{{ aggregated.by_tool_name[tn].failures }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }

      @if (sortedKeys(aggregated.by_policy_decision).length) {
        <section class="oc-panel">
          <h2 class="oc-section-title">By policy decision</h2>
          <div class="oc-table-wrap">
            <table class="oc-table oc-table--static">
              <thead>
                <tr>
                  <th>Decision</th>
                  <th>Evaluations</th>
                  <th>Distinct executions</th>
                </tr>
              </thead>
              <tbody>
                @for (pd of sortedKeys(aggregated.by_policy_decision); track pd) {
                  <tr>
                    <td class="mono">{{ pd }}</td>
                    <td>{{ aggregated.by_policy_decision[pd].evaluation_count }}</td>
                    <td>{{ aggregated.by_policy_decision[pd].distinct_execution_count }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }
    }
  `,
  styles: ``,
})
export class MetricsPage implements OnInit {
  tenantId = '';
  workflowType = '';
  status = '';
  limit = 100;

  aggregated: AggregatedMetricsDto | null = null;
  loading = false;
  loadError: string | null = null;

  constructor(private readonly metricsApi: MetricsApiService) {}

  ngOnInit(): void {
    this.reload();
  }

  sortedKeys(o: object | undefined): string[] {
    if (!o) return [];
    return Object.keys(o).sort();
  }

  pct(v: number | null | undefined): string {
    if (v == null) return '—';
    return `${(v * 100).toFixed(1)}%`;
  }

  policyRowsForWorkflow(): { key: string; workflow: string; decision: string; count: number }[] {
    if (!this.aggregated) return [];
    const out: { key: string; workflow: string; decision: string; count: number }[] = [];
    for (const wf of Object.keys(this.aggregated.by_workflow_type)) {
      const pol = this.aggregated.by_workflow_type[wf].policy_decision_counts;
      for (const decision of Object.keys(pol)) {
        out.push({
          key: `${wf}:${decision}`,
          workflow: wf,
          decision,
          count: pol[decision],
        });
      }
    }
    return out;
  }

  reload(): void {
    this.loading = true;
    this.loadError = null;
    const lim = Math.min(500, Math.max(1, Number(this.limit) || 100));
    this.limit = lim;
    this.metricsApi
      .getAggregatedMetrics({
        tenant_id: this.tenantId.trim() || undefined,
        workflow_type: this.workflowType.trim() || undefined,
        status: this.status.trim() || undefined,
        limit: lim,
      })
      .subscribe({
        next: (res) => {
          this.aggregated = res;
          this.loading = false;
        },
        error: (e: Error) => {
          this.loading = false;
          this.loadError = e.message;
          this.aggregated = null;
        },
      });
  }
}
