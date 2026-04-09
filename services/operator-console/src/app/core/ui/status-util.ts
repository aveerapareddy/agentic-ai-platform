/** Maps platform-reported status strings to shared CSS modifiers (ui-system §7). */

const RUNNING = new Set([
  'created',
  'planning',
  'executing',
  'validating',
  'running',
  'pending',
]);

export function executionStatusModifier(status: string): string {
  const s = (status || '').toLowerCase();
  if (s === 'completed') return 'status--completed';
  if (s === 'failed') return 'status--failed';
  if (s === 'awaiting_approval') return 'status--approval';
  if (s === 'cancelled' || s === 'skipped') return 'status--neutral';
  if (RUNNING.has(s)) return 'status--running';
  return 'status--neutral';
}

export function stepStatusModifier(status: string): string {
  const s = (status || '').toLowerCase();
  if (s === 'succeeded') return 'status--completed';
  if (s === 'failed') return 'status--failed';
  if (s === 'running' || s === 'pending') return 'status--running';
  if (s === 'cancelled' || s === 'skipped') return 'status--neutral';
  return 'status--neutral';
}
