import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ReplayApiService } from '../../core/api/replay-api.service';
import type {
  ReplayDiffCategory,
  ReplayDiffItemDto,
  ReplayDiffSummaryDto,
} from '../../core/models/replay.models';
import {
  categoryLabel,
  diffItemKey,
  groupDiffItemsByCategory,
} from '../../core/ui/replay-diff-util';
import { shortExecutionId } from '../../core/ui/format-util';

@Component({
  selector: 'app-replay-diff-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <p class="back-link">
      <a [routerLink]="['/executions', sourceId]">← Source execution</a>
      <span class="oc-header__sep"> · </span>
      <a [routerLink]="['/executions', replayId]">Replay execution</a>
    </p>
    <h1 class="oc-page-title">Replay diff</h1>
    <p class="oc-page-lead">
      Comparison from <span class="mono">GET /v1/executions/…/replay-diff/…</span> (evaluation-engine
      projection via api-gateway). No client-side diff computation.
    </p>

    @if (loadError) {
      <div class="oc-error" role="alert">{{ loadError }}</div>
    }
    @if (loading) {
      <p class="oc-loading">Loading replay diff…</p>
    } @else if (summary) {
      <div class="oc-stat-row">
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Linked to source</div>
          <div class="oc-stat-card__value">{{ summary.linked_to_source ? 'Yes' : 'No' }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Replay mode</div>
          <div class="oc-stat-card__value">{{ summary.replay_mode ?? '—' }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Total differences</div>
          <div class="oc-stat-card__value">{{ summary.total_differences }}</div>
        </div>
        <div class="oc-stat-card">
          <div class="oc-stat-card__label">Significant</div>
          <div class="oc-stat-card__value">{{ summary.significant_differences }}</div>
        </div>
      </div>

      <p class="oc-meta mono" style="margin-bottom: var(--space-4)">
        Source {{ shortId(summary.source_execution_id) }} · Replay {{ shortId(summary.replay_execution_id) }}
      </p>

      @if (summary.total_differences === 0) {
        <p class="oc-meta oc-empty">No differences reported between these executions.</p>
      }

      @for (group of grouped; track group.category) {
        <section class="oc-panel">
          <h2 class="oc-section-title">{{ categoryLabel(group.category) }}</h2>
          <div class="oc-table-wrap">
            <table class="oc-table oc-table--static">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Title</th>
                  <th>Path</th>
                  <th>Description</th>
                  <th>Values</th>
                </tr>
              </thead>
              <tbody>
                @for (item of group.items; track diffItemKey(item)) {
                  <tr>
                    <td>
                      <span class="oc-severity oc-severity--{{ item.severity }}">{{ item.severity }}</span>
                    </td>
                    <td class="mono">{{ item.title }}</td>
                    <td class="oc-meta mono">{{ item.path }}</td>
                    <td class="oc-meta">{{ item.description }}</td>
                    <td>
                      @if (hasValues(item)) {
                        @if (isExpanded(item)) {
                          <dl class="diff-values">
                            <dt>Source</dt>
                            <dd class="mono">{{ item.source_value ?? '—' }}</dd>
                            <dt>Replay</dt>
                            <dd class="mono">{{ item.replay_value ?? '—' }}</dd>
                          </dl>
                          <button type="button" class="oc-btn oc-btn--compact" (click)="toggle(item)">
                            Hide values
                          </button>
                        } @else {
                          <span class="oc-meta">{{ valuePreview(item) }}</span>
                          <button type="button" class="oc-btn oc-btn--compact" (click)="toggle(item)">
                            Show values
                          </button>
                        }
                      } @else {
                        <span class="oc-meta">—</span>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }
    }
  `,
  styles: `
    .diff-values {
      margin: 0 0 var(--space-2);
      font-size: var(--text-meta);
    }
    .diff-values dt {
      color: var(--muted);
      margin-top: var(--space-2);
    }
    .diff-values dd {
      margin: var(--space-1) 0 0;
      word-break: break-word;
    }
    .oc-btn--compact {
      padding: var(--space-1) var(--space-2);
      font-size: var(--text-label);
    }
    .oc-severity {
      text-transform: uppercase;
      font-size: var(--text-label);
      font-weight: 500;
    }
    .oc-severity--info {
      color: var(--muted);
    }
    .oc-severity--warning {
      color: var(--warn-text);
    }
    .oc-severity--significant {
      color: var(--err-muted);
    }
  `,
})
export class ReplayDiffPage implements OnInit {
  sourceId = '';
  replayId = '';
  summary: ReplayDiffSummaryDto | null = null;
  grouped: { category: ReplayDiffCategory; items: ReplayDiffItemDto[] }[] = [];
  loading = false;
  loadError: string | null = null;
  private expanded = new Set<string>();

  shortId = shortExecutionId;
  categoryLabel = categoryLabel;
  diffItemKey = diffItemKey;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly replayApi: ReplayApiService,
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const src = pm.get('sourceId');
      const rep = pm.get('replayId');
      if (!src || !rep) {
        this.loadError = 'Missing source or replay execution id';
        return;
      }
      this.sourceId = src;
      this.replayId = rep;
      this.load();
    });
  }

  load(): void {
    this.loading = true;
    this.loadError = null;
    this.replayApi.getReplayDiff(this.sourceId, this.replayId).subscribe({
      next: (s) => {
        this.summary = s;
        this.grouped = groupDiffItemsByCategory(s.items);
        this.loading = false;
      },
      error: (e: Error) => {
        this.loading = false;
        this.loadError = e.message;
        this.summary = null;
        this.grouped = [];
      },
    });
  }

  hasValues(item: ReplayDiffItemDto): boolean {
    return item.source_value != null || item.replay_value != null;
  }

  isExpanded(item: ReplayDiffItemDto): boolean {
    return this.expanded.has(diffItemKey(item));
  }

  toggle(item: ReplayDiffItemDto): void {
    const key = diffItemKey(item);
    if (this.expanded.has(key)) {
      this.expanded.delete(key);
    } else {
      this.expanded.add(key);
    }
  }

  valuePreview(item: ReplayDiffItemDto): string {
    const parts: string[] = [];
    if (item.source_value) {
      parts.push(`src: ${truncate(item.source_value, 48)}`);
    }
    if (item.replay_value) {
      parts.push(`replay: ${truncate(item.replay_value, 48)}`);
    }
    return parts.join(' · ') || '—';
  }
}

function truncate(s: string, max: number): string {
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + '…';
}
