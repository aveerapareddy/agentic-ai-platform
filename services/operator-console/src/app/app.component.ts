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
        <span class="oc-header__meta">Executions · Trace · Approvals · api-gateway</span>
      </header>
      <main class="oc-main">
        <router-outlet />
      </main>
    </div>
  `,
  styles: ``,
})
export class AppComponent {}
