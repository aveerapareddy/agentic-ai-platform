import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'executions', pathMatch: 'full' },
  {
    path: 'executions',
    loadComponent: () =>
      import('./pages/executions/executions.page').then((m) => m.ExecutionsPage),
  },
  {
    path: 'executions/:executionId',
    loadComponent: () =>
      import('./pages/execution-detail/execution-detail.page').then((m) => m.ExecutionDetailPage),
  },
  {
    path: 'executions/:sourceId/replay-diff/:replayId',
    loadComponent: () =>
      import('./pages/replay-diff/replay-diff.page').then((m) => m.ReplayDiffPage),
  },
  {
    path: 'live',
    loadComponent: () =>
      import('./pages/live-activity/live-activity.page').then((m) => m.LiveActivityPage),
  },
  {
    path: 'replay',
    loadComponent: () =>
      import('./pages/replay-hub/replay-hub.page').then((m) => m.ReplayHubPage),
  },
  {
    path: 'metrics',
    loadComponent: () => import('./pages/metrics/metrics.page').then((m) => m.MetricsPage),
  },
  {
    path: 'evaluation',
    loadComponent: () => import('./pages/metrics/metrics.page').then((m) => m.MetricsPage),
  },
  {
    path: 'insights',
    loadComponent: () => import('./pages/insights/insights.page').then((m) => m.InsightsPage),
  },
  {
    path: 'policies',
    loadComponent: () => import('./pages/policies/policies.page').then((m) => m.PoliciesPage),
  },
  {
    path: 'approvals',
    loadComponent: () =>
      import('./pages/approvals/approvals.page').then((m) => m.ApprovalsPage),
  },
  {
    path: 'audit',
    loadComponent: () => import('./pages/audit/audit.page').then((m) => m.AuditPage),
  },
  {
    path: 'health',
    loadComponent: () => import('./pages/health/health.page').then((m) => m.HealthPage),
  },
  {
    path: 'streaming',
    loadComponent: () =>
      import('./pages/streaming/streaming.page').then((m) => m.StreamingPage),
  },
  {
    path: 'config',
    loadComponent: () => import('./pages/config/config.page').then((m) => m.ConfigPage),
  },
  { path: '**', redirectTo: 'executions' },
];
