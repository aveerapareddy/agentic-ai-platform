import {
  buildTraceTimelineView,
  classifyTraceEventBucket,
  isErrorLikeTimelineEvent,
  sectionizeStepEvents,
} from './trace-grouping-util';
import type { TraceView } from '../models/execution.models';

describe('trace-grouping-util', () => {
  it('classifies model, tool, policy, and error buckets', () => {
    expect(classifyTraceEventBucket({ event_type: 'model_reasoning' })).toBe('model');
    expect(classifyTraceEventBucket({ event_type: 'tool_call_completed' })).toBe('tool');
    expect(classifyTraceEventBucket({ event_type: 'policy_evaluated' })).toBe('policy');
    expect(
      classifyTraceEventBucket({ event_type: 'tool_call_completed', status: 'failed' }),
    ).toBe('error');
    expect(isErrorLikeTimelineEvent({ event_type: 'governed_outcome', path: 'policy_denied' })).toBe(
      true,
    );
  });

  it('sectionizeStepEvents orders buckets and preserves sort by at', () => {
    const sections = sectionizeStepEvents([
      { event_type: 'step_completed', at: '2026-01-01T10:00:03Z', step_id: 's1' },
      { event_type: 'model_reasoning', at: '2026-01-01T10:00:02Z', step_id: 's1', path: 'model_runtime' },
      { event_type: 'step_started', at: '2026-01-01T10:00:01Z', step_id: 's1' },
    ]);
    expect(sections.map((s) => s.bucket)).toEqual(['execution', 'model']);
    expect(sections[1].events[0]['event_type']).toBe('model_reasoning');
  });

  it('buildTraceTimelineView groups execution and step with counts', () => {
    const trace: TraceView = {
      execution_id: 'e1',
      execution_context: {},
      plans: [],
      steps: [
        {
          step: { step_id: 's1', status: 'completed', step_type: 'reasoning' },
          step_result: { latency_ms: 42 },
        },
      ],
      tool_calls: [],
      policy_evaluations: [],
      approvals: [],
      timeline: [
        { event_type: 'execution_status', at: '2026-01-01T10:00:00Z', status: 'executing' },
        { event_type: 'step_started', at: '2026-01-01T10:00:01Z', step_id: 's1', planner_step_name: 'analyze' },
        { event_type: 'model_reasoning', at: '2026-01-01T10:00:02Z', step_id: 's1', path: 'model_runtime' },
        { event_type: 'step_completed', at: '2026-01-01T10:00:03Z', step_id: 's1' },
      ],
    };
    const view = buildTraceTimelineView(trace);
    expect(view.eventCount).toBe(4);
    expect(view.groups.length).toBe(2);
    expect(view.groups[1].label).toBe('analyze');
    expect(view.groups[1].counts.model).toBe(1);
    expect(view.groups[1].durationMs).toBe(42);
  });
});
