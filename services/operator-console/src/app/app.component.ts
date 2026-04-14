import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  template: `
    <div class="oc-shell">
      <header class="oc-header">
        <a routerLink="/executions" class="oc-header__brand">Operator Console</a>
        <nav class="oc-header__nav">
          <a routerLink="/executions">Executions</a>
          <span class="oc-header__sep">·</span>
          <a routerLink="/metrics">Metrics</a>
        </nav>
        <span class="oc-header__meta">Trace · Approvals · api-gateway</span>
      </header>
      <main class="oc-main">
        <router-outlet />
      </main>
    </div>
  `,
  styles: ``,
})
export class AppComponent {}
