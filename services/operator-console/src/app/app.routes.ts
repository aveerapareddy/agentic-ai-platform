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
    path: 'metrics',
    loadComponent: () => import('./pages/metrics/metrics.page').then((m) => m.MetricsPage),
  },
  { path: '**', redirectTo: 'executions' },
];
