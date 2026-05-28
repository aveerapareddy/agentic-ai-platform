import { Component, Input } from '@angular/core';
import type { CrossExecutionInsightDto } from '../../core/models/insights.models';
import { workflowBadgeClass } from '../../core/ui/workflow-util';

@Component({
  selector: 'app-insight-card',
  standalone: true,
  template: `
    <article class="oc-insight-card" [class]="'oc-insight-card--' + insight.severity">
      <header class="oc-insight-card__head">
        <span class="oc-severity oc-severity--{{ insight.severity }}">{{ insight.severity }}</span>
        <h3 class="oc-insight-card__title">{{ insight.title }}</h3>
      </header>
      <p class="oc-insight-card__why">{{ insight.description }}</p>
      <dl class="oc-insight-card__meta">
        <div>
          <dt>Evidence</dt>
          <dd>{{ insight.evidence_count }}</dd>
        </div>
        @if (insight.suggested_action) {
          <div class="oc-insight-card__action">
            <dt>Suggested action</dt>
            <dd>{{ insight.suggested_action }}</dd>
          </div>
        }
      </dl>
      @if (insight.affected_workflows.length) {
        <div class="oc-insight-card__workflows">
          @for (wf of insight.affected_workflows; track wf) {
            <span [class]="workflowClass(wf)">{{ wf }}</span>
          }
        </div>
      }
      @if (insight.affected_steps.length) {
        <p class="oc-meta oc-insight-card__steps">Steps: {{ insight.affected_steps.join(', ') }}</p>
      }
    </article>
  `,
  styles: ``,
})
export class InsightCardComponent {
  @Input({ required: true }) insight!: CrossExecutionInsightDto;

  workflowClass = workflowBadgeClass;
}
