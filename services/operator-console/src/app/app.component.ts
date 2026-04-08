import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  template: `
    <header class="oc-header">
      <a routerLink="/executions" class="brand">Operator Console</a>
      <span class="sub">Executions · Trace · Approvals (api-gateway)</span>
    </header>
    <main class="oc-main">
      <router-outlet />
    </main>
  `,
  styles: `
    .oc-header {
      display: flex;
      align-items: baseline;
      gap: 1rem;
      padding: 0.75rem 1.25rem;
      border-bottom: 1px solid var(--border);
      background: var(--surface);
    }
    .brand {
      font-weight: 600;
      color: var(--text);
      text-decoration: none;
    }
    .brand:hover {
      color: var(--accent);
      text-decoration: none;
    }
    .sub {
      color: var(--muted);
      font-size: 0.85rem;
    }
    .oc-main {
      padding: 1rem 1.25rem;
      max-width: 1200px;
      margin: 0 auto;
    }
  `,
})
export class AppComponent {}
