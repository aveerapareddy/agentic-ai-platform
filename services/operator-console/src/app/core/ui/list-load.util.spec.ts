import { NEVER, of, throwError } from 'rxjs';
import { withListLoadTimeout } from './list-load.util';

describe('withListLoadTimeout', () => {
  it('passes through successful emissions', (done) => {
    withListLoadTimeout(of({ ok: true }), 5000).subscribe({
      next: (v) => {
        expect(v).toEqual({ ok: true });
        done();
      },
    });
  });

  it('maps timeout errors to a friendly message', (done) => {
    withListLoadTimeout(NEVER, 5).subscribe({
      error: (e: Error) => {
        expect(e.message).toContain('timed out');
        done();
      },
    });
  });

  it('rethrows non-timeout errors', (done) => {
    withListLoadTimeout(throwError(() => new Error('nope')), 5000).subscribe({
      error: (e: Error) => {
        expect(e.message).toBe('nope');
        done();
      },
    });
  });
});
