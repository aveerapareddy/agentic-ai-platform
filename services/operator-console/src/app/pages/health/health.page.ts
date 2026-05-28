import { JsonPipe } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { HealthApiService } from '../../core/api/health-api.service';
import { PageHeaderComponent } from '../../layout/page-header.component';

@Component({
  selector: 'app-health-page',
  standalone: true,
  imports: [JsonPipe, PageHeaderComponent],
  template: `
    <app-page-header
      title="Runtime Health"
      eyebrow="System"
      lead="GET /health/runtime via api-gateway proxy. Component readiness only — not execution semantics."
    />

    <button type="button" class="oc-btn" (click)="reload()" [disabled]="loading">Refresh</button>

    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (loading) {
      <p class="oc-loading">Loading runtime health…</p>
    } @else if (payload) {
      <div class="oc-stat-row">
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Status</div>
          <div class="oc-stat-card__value oc-stat-card__value--sm">{{ statusLabel }}</div>
        </div>
      </div>
      <section class="oc-panel">
        <h2 class="oc-section-title">Response</h2>
        <pre class="oc-json">{{ payload | json }}</pre>
      </section>
    }
  `,
  styles: `
    .oc-stat-card__value--sm {
      font-size: var(--text-body);
      font-weight: 600;
    }
  `,
})
export class HealthPage implements OnInit {
  payload: Record<string, unknown> | null = null;
  loading = false;
  loadError: string | null = null;

  constructor(private readonly health: HealthApiService) {}

  get statusLabel(): string {
    const s = this.payload?.['status'];
    return s != null ? String(s) : '—';
  }

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.loadError = null;
    this.health.getRuntimeHealth().subscribe({
      next: (p) => {
        this.payload = p;
        this.loading = false;
      },
      error: (e: Error) => {
        this.loading = false;
        this.loadError = e.message;
        this.payload = null;
      },
    });
  }
}
