/** Sidebar navigation — maps to existing routes; no new platform semantics. */

export type NavIconId =
  | 'executions'
  | 'live'
  | 'replay'
  | 'metrics'
  | 'insights'
  | 'evaluation'
  | 'policies'
  | 'approvals'
  | 'audit'
  | 'health'
  | 'streaming'
  | 'config';

export interface NavItem {
  label: string;
  path: string;
  icon: NavIconId;
  /** Stable reference for RouterLinkActive (do not allocate in template). */
  routerLinkActiveOptions: { exact: boolean };
}

export interface NavSection {
  id: string;
  title: string;
  items: NavItem[];
}

const exact = { exact: true } as const;
const prefix = { exact: false } as const;

export const NAV_SECTIONS: NavSection[] = [
  {
    id: 'platform',
    title: 'Platform',
    items: [
      { label: 'Executions', path: '/executions', icon: 'executions', routerLinkActiveOptions: prefix },
      { label: 'Live Activity', path: '/live', icon: 'live', routerLinkActiveOptions: exact },
      { label: 'Replay & Diff', path: '/replay', icon: 'replay', routerLinkActiveOptions: exact },
    ],
  },
  {
    id: 'intelligence',
    title: 'Intelligence',
    items: [
      { label: 'Metrics', path: '/metrics', icon: 'metrics', routerLinkActiveOptions: exact },
      { label: 'Mukti Insights', path: '/insights', icon: 'insights', routerLinkActiveOptions: exact },
      { label: 'Evaluation', path: '/evaluation', icon: 'evaluation', routerLinkActiveOptions: exact },
    ],
  },
  {
    id: 'governance',
    title: 'Governance',
    items: [
      { label: 'Policies', path: '/policies', icon: 'policies', routerLinkActiveOptions: exact },
      { label: 'Approvals', path: '/approvals', icon: 'approvals', routerLinkActiveOptions: exact },
      { label: 'Audit / Trace', path: '/audit', icon: 'audit', routerLinkActiveOptions: exact },
    ],
  },
  {
    id: 'system',
    title: 'System',
    items: [
      { label: 'Runtime Health', path: '/health', icon: 'health', routerLinkActiveOptions: exact },
      { label: 'Streaming', path: '/streaming', icon: 'streaming', routerLinkActiveOptions: exact },
      { label: 'Configuration', path: '/config', icon: 'config', routerLinkActiveOptions: exact },
    ],
  },
];
