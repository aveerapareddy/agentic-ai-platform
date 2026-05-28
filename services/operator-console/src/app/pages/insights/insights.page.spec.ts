import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { routes } from '../../app.routes';
import { InsightsPage } from './insights.page';
import { InsightsApiService } from '../../core/api/insights-api.service';

describe('InsightsPage', () => {
  let fixture: ComponentFixture<InsightsPage>;
  let api: jasmine.SpyObj<InsightsApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('InsightsApiService', ['getMuktiInsights']);
    api.getMuktiInsights.and.returnValue(
      of({
        scope_description: 'scope',
        execution_feedback_sample_size: 1,
        top_failure_types: [
          {
            insight_id: 'i1',
            category: 'top_failure_type',
            severity: 'info',
            title: 'step_failure',
            description: 'desc',
            evidence_count: 1,
            affected_workflows: [],
            affected_steps: [],
            suggested_action: null,
            related_execution_ids: [],
            rank_score: 10,
            evidence: {},
          },
        ],
        recurring_patterns: [],
        policy_friction_areas: [],
        model_fallback_concentration: [],
        unstable_workflows_or_steps: [],
        ranked_improvement_suggestions: [],
        insights: [],
      }),
    );
    await TestBed.configureTestingModule({
      imports: [InsightsPage],
      providers: [{ provide: InsightsApiService, useValue: api }, provideRouter(routes)],
    }).compileComponents();
    fixture = TestBed.createComponent(InsightsPage);
  });

  it('renders Mukti insights title and issue surfaces', () => {
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Mukti Insights');
    expect(el.textContent).toContain('Issue surfaces');
    expect(el.textContent).toContain('step_failure');
    expect(api.getMuktiInsights).toHaveBeenCalled();
  });

  it('shows error when API fails', () => {
    api.getMuktiInsights.and.returnValue(throwError(() => new Error('gateway down')));
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('gateway down');
  });
});
