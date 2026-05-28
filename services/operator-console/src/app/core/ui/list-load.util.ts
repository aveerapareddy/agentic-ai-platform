import { Observable, TimeoutError, throwError, timeout } from 'rxjs';
import { catchError } from 'rxjs/operators';

const DEFAULT_LIST_TIMEOUT_MS = 20_000;

/** Prevent hung HTTP calls from leaving pages stuck in initialLoading. */
export function withListLoadTimeout<T>(
  source: Observable<T>,
  ms: number = DEFAULT_LIST_TIMEOUT_MS,
): Observable<T> {
  return source.pipe(
    timeout(ms),
    catchError((err: unknown) => {
      if (err instanceof TimeoutError) {
        return throwError(
          () =>
            new Error(
              `Request timed out after ${ms / 1000}s. Check api-gateway (http://localhost:8080/health/runtime).`,
            ),
        );
      }
      return throwError(() => err);
    }),
  );
}
