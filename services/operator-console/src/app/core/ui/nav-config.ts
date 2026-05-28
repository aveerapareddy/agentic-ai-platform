/** Sidebar navigation — maps to existing routes; no new platform semantics. */

export interface NavItem {
  label: string;
  path: string;
  /** Single-letter or compact glyph for collapsed sidebar */
  icon: string;
  /** Match child routes (e.g. execution detail under /executions) */
  matchPrefix?: boolean;
}

export interface NavSection {
  id: string;
  title: string;
  items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    id: 'platform',
    title: 'Platform',
    items: [
      { label: 'Executions', path: '/executions', icon: 'E', matchPrefix: true },
      { label: 'Live Activity', path: '/live', icon: 'L' },
      { label: 'Replay & Diff', path: '/replay', icon: 'R' },
    ],
  },
  {
    id: 'intelligence',
    title: 'Intelligence',
    items: [
      { label: 'Metrics', path: '/metrics', icon: 'M' },
      { label: 'Mukti Insights', path: '/insights', icon: 'I' },
      { label: 'Evaluation', path: '/evaluation', icon: 'V' },
    ],
  },
  {
    id: 'governance',
    title: 'Governance',
    items: [
      { label: 'Policies', path: '/policies', icon: 'P' },
      { label: 'Approvals', path: '/approvals', icon: 'A' },
      { label: 'Audit / Trace', path: '/audit', icon: 'T' },
    ],
  },
  {
    id: 'system',
    title: 'System',
    items: [
      { label: 'Runtime Health', path: '/health', icon: 'H' },
      { label: 'Streaming', path: '/streaming', icon: 'S' },
      { label: 'Configuration', path: '/config', icon: 'C' },
    ],
  },
];
