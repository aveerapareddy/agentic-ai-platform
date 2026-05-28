import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PageHeaderComponent } from '../../layout/page-header.component';

@Component({
  selector: 'app-audit-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent],
  template: `
    <app-page-header
      title="Audit / Trace"
      eyebrow="Governance"
      lead="Full execution traces are persisted by the platform and exposed via GET /v1/executions/:id/trace. Use the execution explorer to inspect authoritative records."
    />

    <div class="oc-panel oc-audit-actions">
      <h2 class="oc-section-title">Trace inspection</h2>
      <p class="oc-meta">
        Timeline events, tool calls, policy evaluations, and approvals are server projections — not recomputed in the
        browser.
      </p>
      <div class="oc-btn-row">
        <a routerLink="/executions" class="oc-btn oc-btn--primary">Open executions</a>
        <a routerLink="/live" class="oc-btn">Live activity</a>
      </div>
    </div>

    <section class="oc-panel">
      <h2 class="oc-section-title">What to inspect</h2>
      <ul class="oc-audit-list">
        <li><span class="oc-label">Steps & validation</span> — execution detail → Steps, Validation summary</li>
        <li><span class="oc-label">Timeline</span> — grouped trace with model, tool, policy, and error buckets</li>
        <li><span class="oc-label">Replay lineage</span> — replay panel and replay-diff when a child execution exists</li>
        <li><span class="oc-label">Metrics</span> — evaluation-engine aggregates per execution and platform rollups</li>
      </ul>
    </section>
  `,
  styles: `
    .oc-audit-actions {
      margin-bottom: var(--space-4);
    }
    .oc-btn-row {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-3);
      margin-top: var(--space-4);
    }
    .oc-audit-list {
      margin: 0;
      padding: 0;
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: var(--space-3);
    }
    .oc-audit-list li {
      font-size: var(--text-body);
      color: var(--text);
    }
    .oc-audit-list .oc-label {
      display: block;
      margin-bottom: var(--space-1);
    }
  `,
})
export class AuditPage {}
