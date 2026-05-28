import { groupDiffItemsByCategory } from './replay-diff-util';
import type { ReplayDiffItemDto } from '../models/replay.models';

describe('groupDiffItemsByCategory', () => {
  it('orders categories and groups items', () => {
    const items: ReplayDiffItemDto[] = [
      {
        category: 'input',
        severity: 'warning',
        title: 'a',
        description: '',
        source_value: null,
        replay_value: null,
        path: 'input.x',
        related_step_id: null,
        related_tool_call_id: null,
      },
      {
        category: 'lineage',
        severity: 'info',
        title: 'b',
        description: '',
        source_value: null,
        replay_value: null,
        path: 'lineage',
        related_step_id: null,
        related_tool_call_id: null,
      },
    ];
    const grouped = groupDiffItemsByCategory(items);
    expect(grouped[0].category).toBe('lineage');
    expect(grouped[1].category).toBe('input');
  });
});
