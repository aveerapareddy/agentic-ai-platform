/** Display-only workflow styling — no semantic inference. */

export function workflowBadgeClass(workflowType: string): string {
  const w = workflowType.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return `wf-badge wf-badge--${w || 'default'}`;
}

export function workflowLabel(workflowType: string): string {
  return workflowType.replace(/_/g, ' ');
}
