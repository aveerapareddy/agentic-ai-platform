import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import type { NavIconId } from '../../core/ui/nav-config';

/**
 * Minimal stroke icons (Lucide-style paths, inline SVG — no icon library dependency).
 */
@Component({
  selector: 'app-nav-icon',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      class="oc-nav-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      @switch (icon) {
        @case ('executions') {
          <path d="M8 6h13" /><path d="M8 12h13" /><path d="M8 18h13" /><path d="M3 6h.01" /><path
            d="M3 12h.01"
          /><path d="M3 18h.01" />
        }
        @case ('live') {
          <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a25.82 25.82 0 0 1-19.24 0l-2.35-8.36A2 2 0 0 0 4.49 12H2" />
        }
        @case ('replay') {
          <path d="m16 3 4 4-4 4" /><path d="M20 7H4" /><path d="m8 21-4-4 4-4" /><path d="M4 17h16" />
        }
        @case ('metrics') {
          <path d="M12 20V10" /><path d="M18 20V4" /><path d="M6 20v-4" />
        }
        @case ('insights') {
          <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588 4 4 0 0 0 7.636 2.106 3 3 0 0 0 .164-1.858 3 3 0 0 0 .164 1.858 4 4 0 0 0 7.636-2.106 4 4 0 0 0 .556-6.588 4 4 0 0 0-2.526-5.77A3 3 0 1 0 12 5Z" />
        }
        @case ('evaluation') {
          <circle cx="12" cy="12" r="10" /><path d="m9 12 2 2 4-4" />
        }
        @case ('policies') {
          <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
        }
        @case ('approvals') {
          <path d="M21.801 10A10 10 0 1 1 17 3.335" /><path d="m9 11 2 2 4-4" />
        }
        @case ('audit') {
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path
            d="M10 13H8"
          /><path d="M16 17H8" /><path d="M16 13h-2" />
        }
        @case ('health') {
          <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" /><path
            d="M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"
          />
        }
        @case ('streaming') {
          <path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9" /><path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5" /><circle cx="12" cy="12" r="2" /><path
            d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5"
          /><path d="M19.1 4.9C23 8.8 23 15.1 19.1 19" />
        }
        @case ('config') {
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" />
        }
      }
    </svg>
  `,
  styles: `
    :host {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .oc-nav-icon {
      width: 1.125rem;
      height: 1.125rem;
    }
  `,
})
export class NavIconComponent {
  @Input({ required: true }) icon!: NavIconId;
}
