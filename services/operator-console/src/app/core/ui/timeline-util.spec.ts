import {
  groupTimelineByStep,
  modelReasoningPathForStep,
  stepIdsInOrder,
  timelineEventSummary,
} from './timeline-util';

describe('timeline-util', () => {
  it('groups timeline by step and execution bucket', () => {
    const timeline = [
      { event_type: 'execution_status', at: '2026-01-01T10:00:00Z', status: 'executing' },
      { event_type: 'step_started', at: '2026-01-01T10:00:01Z', step_id: 's1', planner_step_name: 'analyze' },
      { event_type: 'model_reasoning', at: '2026-01-01T10:00:02Z', step_id: 's1', path: 'model_runtime', task: 't' },
      { event_type: 'step_completed', at: '2026-01-01T10:00:03Z', step_id: 's1' },
    ];
    const stepOrder = ['s1'];
    const groups = groupTimelineByStep(timeline, stepOrder);
    expect(groups.length).toBe(2);
    expect(groups[0].key).toBe('__execution__');
    expect(groups[0].events.length).toBe(1);
    expect(groups[1].key).toBe('s1');
    expect(groups[1].label).toBe('analyze');
    expect(groups[1].events.length).toBe(3);
  });

  it('stepIdsInOrder preserves trace.steps order', () => {
    const rows = [{ step: { step_id: 'b' } }, { step: { step_id: 'a' } }];
    expect(stepIdsInOrder(rows)).toEqual(['b', 'a']);
  });

  it('modelReasoningPathForStep reads last model_reasoning path', () => {
    const timeline = [
      { event_type: 'model_reasoning', at: '1', step_id: 'x', path: 'model_runtime' },
      { event_type: 'model_reasoning', at: '2', step_id: 'x', path: 'deterministic_fallback' },
    ];
    expect(modelReasoningPathForStep(timeline, 'x')).toBe('deterministic_fallback');
  });

  it('timelineEventSummary covers key event types', () => {
    expect(timelineEventSummary({ event_type: 'policy_evaluated', decision: 'allow' })).toContain('allow');
    expect(timelineEventSummary({ event_type: 'approval_required' })).toContain('Approval');
  });
});
