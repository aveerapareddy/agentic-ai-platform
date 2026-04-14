import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { routes } from '../../app.routes';
import { MetricsPage } from './metrics.page';
import { MetricsApiService } from '../../core/api/metrics-api.service';

describe('MetricsPage', () => {
  let fixture: ComponentFixture<MetricsPage>;
  let api: jasmine.SpyObj<MetricsApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('MetricsApiService', ['getAggregatedMetrics']);
    api.getAggregatedMetrics.and.returnValue(
      of({
        executions_in_scope: 1,
        by_workflow_type: {
          wf: {
            execution_count: 1,
            failed_execution_count: 0,
            mean_model_fallback_rate: null,
            mean_tool_success_rate: null,
            policy_decision_counts: {},
          },
        },
        by_step_type: {},
        by_tool_name: {},
        by_policy_decision: {},
      }),
    );
    await TestBed.configureTestingModule({
      imports: [MetricsPage],
      providers: [{ provide: MetricsApiService, useValue: api }, provideRouter(routes)],
    }).compileComponents();
    fixture = TestBed.createComponent(MetricsPage);
  });

  it('renders title and summary after load', () => {
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Platform metrics');
    expect(el.textContent).toContain('Executions in scope');
    expect(api.getAggregatedMetrics).toHaveBeenCalled();
  });

  it('shows error when API fails', () => {
    api.getAggregatedMetrics.and.returnValue(throwError(() => new Error('gateway down')));
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('gateway down');
  });
});
