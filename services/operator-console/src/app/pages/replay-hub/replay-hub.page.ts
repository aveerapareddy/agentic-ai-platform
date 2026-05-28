import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { PageHeaderComponent } from '../../layout/page-header.component';

@Component({
  selector: 'app-replay-hub-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent],
  template: `
    <app-page-header
      title="Replay & Diff"
      eyebrow="Platform"
      lead="Request replay from execution detail (POST /v1/executions/:id/replay). Diff is server-computed via GET …/replay-diff/…"
    />

    <div class="oc-panel">
      <h2 class="oc-section-title">Investigation flow</h2>
      <ol class="oc-replay-flow">
        <li>Open a <a routerLink="/executions">source execution</a> and use the Replay panel (exact or investigative).</li>
        <li>Open the child replay execution from the link returned after create.</li>
        <li>Compare with <span class="mono">/executions/:source/replay-diff/:replay</span> — grouped by category and severity.</li>
      </ol>
      <a routerLink="/executions" class="oc-btn oc-btn--primary">Browse executions</a>
    </div>
  `,
  styles: `
    .oc-replay-flow {
      margin: 0 0 var(--space-4);
      padding-left: var(--space-5);
      color: var(--text);
      line-height: 1.6;
    }
    .oc-replay-flow a {
      color: var(--accent-muted);
    }
  `,
})
export class ReplayHubPage {}
