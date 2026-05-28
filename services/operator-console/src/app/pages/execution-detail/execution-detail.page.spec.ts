import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';
import { ExecutionDetailPage } from './execution-detail.page';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import { MetricsApiService } from '../../core/api/metrics-api.service';

describe('ExecutionDetailPage (metrics wiring)', () => {
  let fixture: ComponentFixture<ExecutionDetailPage>;
  let api: jasmine.SpyObj<ExecutionApiService>;
  let metricsApi: jasmine.SpyObj<MetricsApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('ExecutionApiService', ['getExecution', 'getTrace']);
    metricsApi = jasmine.createSpyObj('MetricsApiService', ['getExecutionMetrics']);

    api.getExecution.and.returnValue(
      of({
        execution_id: 'e1',
        workflow_type: 'generic',
        status: 'completed',
        execution_context_id: 'c1',
        current_plan_id: null,
        parent_execution_id: null,
        input: {},
        result: null,
        validation_summary: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        completed_at: null,
        cancelled_at: null,
      }),
    );
    api.getTrace.and.returnValue(
      of({
        execution_id: 'e1',
        execution_context: { tenant_id: 't1' },
        plans: [],
        steps: [],
        tool_calls: [],
        policy_evaluations: [],
        approvals: [],
        timeline: [],
      }),
    );
    metricsApi.getExecutionMetrics.and.returnValue(
      of({
        execution_id: 'e1',
        workflow_type: 'generic',
        execution_status: 'completed',
        tenant_id: 't1',
        model_reasoning_event_count: 0,
        model_reasoning_fallback_event_count: 0,
        model_fallback_rate: null,
        validation_success: true,
        validation_detail: 'ok',
        policy_decisions: [],
        policy_outcome: null,
        tool_calls_total: 0,
        tool_calls_success: 0,
        tool_success_rate: null,
        step_latency_sum_ms: null,
        wall_clock_ms: null,
        total_latency_ms: null,
        computation_notes: [],
      }),
    );
    await TestBed.configureTestingModule({
      imports: [ExecutionDetailPage],
      providers: [
        { provide: ExecutionApiService, useValue: api },
        { provide: MetricsApiService, useValue: metricsApi },
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap({ executionId: 'e1' })) },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ExecutionDetailPage);
  });

  it('renders evaluation metrics section and calls gateway metrics API', async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Evaluation metrics');
    expect(el.textContent).toContain('Model fallback rate');
    expect(metricsApi.getExecutionMetrics).toHaveBeenCalledWith('e1');
    expect(metricsApi.getExecutionMetrics).toHaveBeenCalledTimes(1);
  });
});
