import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TraceTimelineComponent } from './trace-timeline.component';
import type { TraceView } from '../../core/models/execution.models';

const sampleTrace: TraceView = {
  execution_id: 'e1',
  execution_context: {},
  plans: [],
  steps: [{ step: { step_id: 's1', status: 'completed' }, step_result: null }],
  tool_calls: [],
  policy_evaluations: [],
  approvals: [],
  timeline: [
    { event_type: 'execution_status', at: '2026-01-01T10:00:00Z', status: 'executing' },
    {
      event_type: 'model_reasoning',
      at: '2026-01-01T10:00:01Z',
      step_id: 's1',
      path: 'model_runtime',
      task: 'analyze',
    },
    {
      event_type: 'policy_evaluated',
      at: '2026-01-01T10:00:02Z',
      step_id: 's1',
      decision: 'allow',
    },
  ],
};

describe('TraceTimelineComponent', () => {
  let fixture: ComponentFixture<TraceTimelineComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TraceTimelineComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(TraceTimelineComponent);
  });

  it('renders grouped sections and event type labels', () => {
    fixture.componentRef.setInput('trace', sampleTrace);
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Trace timeline');
    expect(el.textContent).toContain('Execution & steps');
    expect(el.textContent).toContain('Model runtime');
    expect(el.textContent).toContain('Policy & approval');
    expect(el.textContent).toContain('model_reasoning');
    expect(el.textContent).toContain('policy_evaluated');
  });

  it('shows loading and error states', () => {
    fixture.componentRef.setInput('loading', true);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Loading trace');

    fixture.componentRef.setInput('loading', false);
    fixture.componentRef.setInput('error', 'Trace unavailable');
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Trace unavailable');
  });

  it('expands payload details on demand', () => {
    fixture.componentRef.setInput('trace', sampleTrace);
    fixture.detectChanges();
    const details = (fixture.nativeElement as HTMLElement).querySelectorAll('details.tl-event');
    expect(details.length).toBeGreaterThan(0);
    const first = details[0] as HTMLDetailsElement;
    expect(first.open).toBeFalse();
    first.open = true;
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Raw JSON');
  });
});
