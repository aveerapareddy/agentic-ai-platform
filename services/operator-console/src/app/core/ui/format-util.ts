/** Display helpers; identifiers may use monospace per ui-system §3. */

export function shortExecutionId(id: string, head = 8, tail = 6): string {
  if (!id || id.length <= head + tail + 1) return id;
  return `${id.slice(0, head)}…${id.slice(-tail)}`;
}

export function formatIsoShort(iso: string | null | undefined): string {
  if (iso == null || iso === '') return '—';
  if (iso.length >= 19) return iso.slice(0, 19).replace('T', ' ');
  return iso;
}
