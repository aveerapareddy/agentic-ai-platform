import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PageHeaderComponent } from '../../layout/page-header.component';

@Component({
  selector: 'app-streaming-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent],
  template: `
    <app-page-header
      title="Streaming"
      eyebrow="System"
      lead="Execution detail subscribes to GET /v1/executions/:id/stream (SSE) until a terminal state. Parsed events update status and append trace rows."
    />

    <div class="oc-panel">
      <h2 class="oc-section-title">SSE contract</h2>
      <dl class="oc-dl oc-dl--wide">
        <dt>Endpoint</dt>
        <dd class="mono">GET /v1/executions/:execution_id/stream</dd>
        <dt>Events</dt>
        <dd>execution_updated, step_updated, trace_event, approval_required, terminal events</dd>
        <dt>Indicator</dt>
        <dd>Live badge on execution detail while subscribed</dd>
      </dl>
      <div class="oc-btn-row">
        <a routerLink="/live" class="oc-btn oc-btn--primary">Live activity</a>
        <a routerLink="/executions" class="oc-btn">Executions</a>
      </div>
    </div>
  `,
  styles: `
    .oc-dl--wide {
      grid-template-columns: 8rem 1fr;
    }
    .oc-btn-row {
      display: flex;
      gap: var(--space-3);
      margin-top: var(--space-4);
    }
  `,
})
export class StreamingPage {}
