import type { ReplayDiffCategory, ReplayDiffItemDto } from '../models/replay.models';

export const REPLAY_DIFF_CATEGORY_ORDER: ReplayDiffCategory[] = [
  'lineage',
  'execution_status',
  'input',
  'plan',
  'step',
  'model_reasoning',
  'tool_call',
  'policy',
  'validation',
  'result',
];

export function categoryLabel(category: ReplayDiffCategory): string {
  return category.replace(/_/g, ' ');
}

export function groupDiffItemsByCategory(
  items: ReplayDiffItemDto[],
): { category: ReplayDiffCategory; items: ReplayDiffItemDto[] }[] {
  const buckets = new Map<ReplayDiffCategory, ReplayDiffItemDto[]>();
  for (const item of items) {
    const list = buckets.get(item.category) ?? [];
    list.push(item);
    buckets.set(item.category, list);
  }
  const out: { category: ReplayDiffCategory; items: ReplayDiffItemDto[] }[] = [];
  for (const cat of REPLAY_DIFF_CATEGORY_ORDER) {
    const rows = buckets.get(cat);
    if (rows?.length) {
      out.push({ category: cat, items: rows });
    }
  }
  return out;
}

export function diffItemKey(item: ReplayDiffItemDto): string {
  return `${item.category}:${item.path}:${item.title}`;
}
