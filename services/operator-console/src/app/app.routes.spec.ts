import { routes } from './app.routes';

describe('app.routes', () => {
  it('defines core platform and intelligence routes', () => {
    const paths = routes.map((r) => r.path);
    expect(paths).toContain('executions');
    expect(paths).toContain('executions/:executionId');
    expect(paths).toContain('executions/:sourceId/replay-diff/:replayId');
    expect(paths).toContain('live');
    expect(paths).toContain('replay');
    expect(paths).toContain('metrics');
    expect(paths).toContain('evaluation');
    expect(paths).toContain('insights');
    expect(paths).toContain('policies');
    expect(paths).toContain('approvals');
    expect(paths).toContain('audit');
    expect(paths).toContain('health');
    expect(paths).toContain('streaming');
    expect(paths).toContain('config');
  });

  it('defaults to executions', () => {
    const root = routes.find((r) => r.path === '');
    expect(root?.redirectTo).toBe('executions');
  });
});
