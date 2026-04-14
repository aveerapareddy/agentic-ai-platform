import { HttpClient, HttpParams } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE_URL } from './api-base-url.token';
import type { AggregatedMetricsDto, ExecutionMetricsDto } from '../models/metrics.models';
import type { ApiErrorBody } from '../models/execution.models';

export interface AggregatedMetricsQuery {
  tenant_id?: string;
  workflow_type?: string;
  status?: string;
  limit?: number;
}

@Injectable({ providedIn: 'root' })
export class MetricsApiService {
  constructor(
    private readonly http: HttpClient,
    @Inject(API_BASE_URL) private readonly baseUrl: string,
  ) {}

  private url(path: string): string {
    const base = this.baseUrl.replace(/\/$/, '');
    return `${base}${path}`;
  }

  getExecutionMetrics(executionId: string): Observable<ExecutionMetricsDto> {
    return this.http
      .get<ExecutionMetricsDto>(this.url(`/v1/executions/${executionId}/metrics`))
      .pipe(catchError((e) => this.mapError(e)));
  }

  getAggregatedMetrics(query: AggregatedMetricsQuery): Observable<AggregatedMetricsDto> {
    let params = new HttpParams();
    if (query.tenant_id) params = params.set('tenant_id', query.tenant_id);
    if (query.workflow_type) params = params.set('workflow_type', query.workflow_type);
    if (query.status) params = params.set('status', query.status);
    if (query.limit != null) params = params.set('limit', String(query.limit));
    return this.http
      .get<AggregatedMetricsDto>(this.url('/v1/metrics'), { params })
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
        msg = (d as ApiErrorBody).error?.message ?? null;
      }
    }
    if (!msg && raw && typeof raw === 'object' && 'error' in raw) {
      msg = (raw as ApiErrorBody).error?.message ?? null;
    }
    if (!msg && typeof raw === 'string') msg = raw;
    return throwError(() => new Error(msg || httpErr?.message || 'Request failed'));
  }
}
