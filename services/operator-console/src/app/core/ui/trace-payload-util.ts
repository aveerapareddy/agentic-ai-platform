/** Format gateway timeline event fields for readable, collapsed-by-default display. */

import type { TimelineEvent } from './timeline-util';

const SKIP_KEYS = new Set(['event_type', 'at']);

export interface PayloadFieldRow {
  key: string;
  value: string;
  multiline: boolean;
}

export function payloadFieldRows(ev: TimelineEvent): PayloadFieldRow[] {
  const rows: PayloadFieldRow[] = [];
  for (const [key, raw] of Object.entries(ev)) {
    if (SKIP_KEYS.has(key)) continue;
    const { text, multiline } = formatPayloadValue(raw);
    rows.push({ key, value: text, multiline });
  }
  return rows;
}

export function hasPayloadDetails(ev: TimelineEvent): boolean {
  return payloadFieldRows(ev).length > 0;
}

function formatPayloadValue(raw: unknown): { text: string; multiline: boolean } {
  if (raw == null) return { text: '—', multiline: false };
  if (typeof raw === 'string') {
    if (raw.length > 120) return { text: raw, multiline: true };
    return { text: raw, multiline: false };
  }
  if (typeof raw === 'number' || typeof raw === 'boolean') {
    return { text: String(raw), multiline: false };
  }
  try {
    const json = JSON.stringify(raw, null, 2);
    const multiline = json.includes('\n') || json.length > 80;
    return { text: json, multiline };
  } catch {
    return { text: String(raw), multiline: false };
  }
}
