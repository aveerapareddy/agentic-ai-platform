import { HttpClient } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE_URL } from './api-base-url.token';
import type {
  PolicyListResponse,
  PolicySimulateRequest,
  PolicySimulateResponse,
} from '../models/policy.models';
import type { ApiErrorBody } from '../models/execution.models';

@Injectable({ providedIn: 'root' })
export class PolicyApiService {
  constructor(
    private readonly http: HttpClient,
    @Inject(API_BASE_URL) private readonly baseUrl: string,
  ) {}

  private url(path: string): string {
    const base = this.baseUrl.replace(/\/$/, '');
    return `${base}${path}`;
  }

  listPolicies(): Observable<PolicyListResponse> {
    return this.http
      .get<PolicyListResponse>(this.url('/v1/policies'))
      .pipe(catchError((e) => this.mapError(e)));
  }

  simulate(body: PolicySimulateRequest): Observable<PolicySimulateResponse> {
    return this.http
      .post<PolicySimulateResponse>(this.url('/v1/policies/simulate'), body)
      .pipe(catchError((e) => this.mapError(e)));
  }

  private mapError(err: unknown): Observable<never> {
    const httpErr = err as {
      error?: ApiErrorBody | { detail?: ApiErrorBody | string };
      message?: string;
    };
    const raw = httpErr?.error;
    let msg: string | null = null;
    if (raw && typeof raw === 'object' && 'detail' in raw) {
      const d = raw.detail;
      if (typeof d === 'string') msg = d;
      else if (d && typeof d === 'object' && 'error' in d) {
        const inner = d.error as { message?: string };
        msg = inner?.message ?? null;
      }
    }
    return throwError(() => new Error(msg || httpErr?.message || 'policy API error'));
  }
}
