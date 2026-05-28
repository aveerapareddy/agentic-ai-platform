import { Component, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs/operators';
import { NAV_SECTIONS, type NavItem } from '../core/ui/nav-config';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="oc-app" [class.oc-app--collapsed]="sidebarCollapsed()">
      <aside class="oc-sidebar" aria-label="Primary navigation">
        <div class="oc-sidebar__brand">
          <a routerLink="/executions" class="oc-sidebar__logo" title="Operator Console">
            <span class="oc-sidebar__mark" aria-hidden="true">OC</span>
            @if (!sidebarCollapsed()) {
              <span class="oc-sidebar__title">Operator Console</span>
            }
          </a>
          <button
            type="button"
            class="oc-sidebar__toggle"
            (click)="toggleSidebar()"
            [attr.aria-expanded]="!sidebarCollapsed()"
            aria-label="Toggle sidebar"
          >
            {{ sidebarCollapsed() ? '›' : '‹' }}
          </button>
        </div>

        <nav class="oc-sidebar__nav">
          @for (section of sections; track section.id) {
            @if (!sidebarCollapsed()) {
              <div class="oc-sidebar__section-label">{{ section.title }}</div>
            }
            <ul class="oc-sidebar__list">
              @for (item of section.items; track item.path + item.label) {
                <li>
                  <a
                    [routerLink]="item.path"
                    routerLinkActive="oc-sidebar__link--active"
                    [routerLinkActiveOptions]="linkActiveOptions(item)"
                    class="oc-sidebar__link"
                    [title]="item.label"
                  >
                    <span class="oc-sidebar__icon" aria-hidden="true">{{ item.icon }}</span>
                    @if (!sidebarCollapsed()) {
                      <span class="oc-sidebar__label">{{ item.label }}</span>
                    }
                  </a>
                </li>
              }
            </ul>
          }
        </nav>

        <footer class="oc-sidebar__foot">
          @if (!sidebarCollapsed()) {
            <span class="oc-meta">api-gateway · read-only ops</span>
          }
        </footer>
      </aside>

      <div class="oc-workspace">
        <header class="oc-topbar">
          <span class="oc-topbar__crumb oc-meta">{{ pageTitle() }}</span>
          @if (liveRoute()) {
            <span class="oc-live-pill" title="Live Activity uses execution SSE">SSE</span>
          }
        </header>
        <main class="oc-main oc-main--wide">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styles: ``,
})
export class AppShellComponent {
  readonly sections = NAV_SECTIONS;
  readonly sidebarCollapsed = signal(false);
  readonly pageTitle = signal('Platform');
  readonly liveRoute = signal(false);

  constructor(private readonly router: Router) {
    this.router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd)).subscribe(() => {
      this.syncChrome();
    });
    this.syncChrome();
  }

  toggleSidebar(): void {
    this.sidebarCollapsed.update((v) => !v);
  }

  linkActiveOptions(item: NavItem): { exact: boolean } {
    return { exact: !item.matchPrefix };
  }

  private syncChrome(): void {
    const url = this.router.url.split('?')[0];
    this.liveRoute.set(url.startsWith('/live') || /\/executions\/[^/]+$/.test(url));
    let title = 'Platform';
    for (const section of NAV_SECTIONS) {
      for (const item of section.items) {
        if (url === item.path || (item.matchPrefix && url.startsWith(item.path + '/'))) {
          title = item.label;
          break;
        }
      }
    }
    if (url.includes('/replay-diff/')) {
      title = 'Replay diff';
    }
    this.pageTitle.set(title);
  }
}
