import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExecutionMetricsComponent } from './execution-metrics.component';

describe('ExecutionMetricsComponent', () => {
  let fixture: ComponentFixture<ExecutionMetricsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExecutionMetricsComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(ExecutionMetricsComponent);
  });

  it('renders metric labels when metrics provided', () => {
    fixture.componentRef.setInput('metrics', {
      execution_id: 'x',
      workflow_type: 'generic',
      execution_status: 'completed',
      tenant_id: null,
      model_reasoning_event_count: 0,
      model_reasoning_fallback_event_count: 0,
      model_fallback_rate: 0.25,
      validation_success: true,
      validation_detail: 'ok',
      policy_decisions: [],
      policy_outcome: 'allow',
      tool_calls_total: 2,
      tool_calls_success: 2,
      tool_success_rate: 1,
      step_latency_sum_ms: 10,
      wall_clock_ms: 100,
      total_latency_ms: 100,
      computation_notes: [],
    });
    fixture.componentRef.setInput('loading', false);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Model fallback rate');
    expect(el.textContent).toContain('Policy outcome');
    expect(el.textContent).toContain('Total latency');
  });

  it('shows loading text when loading', () => {
    fixture.componentRef.setInput('loading', true);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Loading metrics');
  });

  it('shows server notes when computation_notes present', () => {
    fixture.componentRef.setInput('metrics', {
      execution_id: 'x',
      workflow_type: 'generic',
      execution_status: 'completed',
      tenant_id: null,
      model_reasoning_event_count: 0,
      model_reasoning_fallback_event_count: 0,
      model_fallback_rate: null,
      validation_success: null,
      validation_detail: null,
      policy_decisions: [],
      policy_outcome: null,
      tool_calls_total: 0,
      tool_calls_success: 0,
      tool_success_rate: null,
      step_latency_sum_ms: null,
      wall_clock_ms: null,
      total_latency_ms: null,
      computation_notes: ['High model fallback rate for this execution.'],
    });
    fixture.componentRef.setInput('loading', false);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Anomaly flags');
    expect(el.textContent).toContain('High model fallback rate');
  });
});
