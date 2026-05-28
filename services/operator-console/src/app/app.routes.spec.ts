import { routes } from './app.routes';

describe('app.routes', () => {
  it('defines executions explorer and detail', () => {
    const paths = routes.map((r) => r.path);
    expect(paths).toContain('executions');
    expect(paths).toContain('executions/:executionId');
    expect(paths).toContain('metrics');
    expect(paths).toContain('insights');
    expect(paths).toContain('policies');
    expect(paths).toContain('executions/:sourceId/replay-diff/:replayId');
  });

  it('defaults to executions', () => {
    const root = routes.find((r) => r.path === '');
    expect(root?.redirectTo).toBe('executions');
  });
});
