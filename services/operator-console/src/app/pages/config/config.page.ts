import { Component } from '@angular/core';
import { DEV_AUTH_HEADERS } from '../../core/api/dev-auth-headers';
import { PageHeaderComponent } from '../../layout/page-header.component';

@Component({
  selector: 'app-config-page',
  standalone: true,
  imports: [PageHeaderComponent],
  template: `
    <app-page-header
      title="Configuration"
      eyebrow="System"
      lead="Local dev identity headers forwarded to api-gateway. Production deployments must inject identity at the edge — UI is not authoritative."
    />

    <section class="oc-panel">
      <h2 class="oc-section-title">Dev auth headers</h2>
      <dl class="oc-dl oc-dl--wide">
        @for (row of headerRows; track row.key) {
          <dt>{{ row.key }}</dt>
          <dd class="mono">{{ row.value }}</dd>
        }
      </dl>
    </section>

    <section class="oc-panel">
      <h2 class="oc-section-title">API base</h2>
      <p class="oc-meta">
        Empty <span class="mono">API_BASE_URL</span> uses same-origin proxy (<span class="mono">ng serve</span> → gateway).
        Docker nginx proxies <span class="mono">/v1</span> and <span class="mono">/health/</span>.
      </p>
    </section>
  `,
  styles: `
    .oc-dl--wide {
      grid-template-columns: 11rem 1fr;
    }
  `,
})
export class ConfigPage {
  readonly headerRows = Object.entries(DEV_AUTH_HEADERS).map(([key, value]) => ({ key, value }));
}
