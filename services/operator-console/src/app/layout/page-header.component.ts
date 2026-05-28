import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-page-header',
  standalone: true,
  template: `
    <header class="oc-page-header">
      <div class="oc-page-header__main">
        @if (eyebrow) {
          <p class="oc-page-header__eyebrow">{{ eyebrow }}</p>
        }
        <h1 class="oc-page-title">{{ title }}</h1>
        @if (lead) {
          <p class="oc-page-lead">{{ lead }}</p>
        }
      </div>
      <div class="oc-page-header__actions">
        <ng-content />
      </div>
    </header>
  `,
  styles: ``,
})
export class PageHeaderComponent {
  @Input({ required: true }) title = '';
  @Input() lead: string | null = null;
  @Input() eyebrow: string | null = null;
}
