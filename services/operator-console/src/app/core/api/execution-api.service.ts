import { HttpClient, HttpParams } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE_URL } from './api-base-url.token';
import type {
  ApprovalSubmitBody,
  ApiErrorBody,
  ExecutionDetail,
  ListExecutionsResponse,
  TraceView,
} from '../models/execution.models';

export interface ApprovalCreatedResponse {
  approval_id: string;
  execution_id: string;
  decision: string;
  decided_at: string;
}

@Injectable({ providedIn: 'root' })
export class ExecutionApiService {
  constructor(
    private readonly http: HttpClient,
    @Inject(API_BASE_URL) private readonly baseUrl: string,
  ) {}

  private url(path: string): string {
    const base = this.baseUrl.replace(/\/$/, '');
    return `${base}${path}`;
  }

  listExecutions(filters: {
    tenant_id?: string;
    workflow_type?: string;
    status?: string;
    limit?: number;
  }): Observable<ListExecutionsResponse> {
    let params = new HttpParams();
    if (filters.tenant_id) params = params.set('tenant_id', filters.tenant_id);
    if (filters.workflow_type) params = params.set('workflow_type', filters.workflow_type);
    if (filters.status) params = params.set('status', filters.status);
    if (filters.limit != null) params = params.set('limit', String(filters.limit));
    return this.http
      .get<ListExecutionsResponse>(this.url('/v1/executions'), { params })
      .pipe(catchError((e) => this.mapError(e)));
  }

  getExecution(executionId: string): Observable<ExecutionDetail> {
    return this.http
      .get<ExecutionDetail>(this.url(`/v1/executions/${executionId}`))
      .pipe(catchError((e) => this.mapError(e)));
  }

  getTrace(executionId: string): Observable<TraceView> {
    return this.http
      .get<TraceView>(this.url(`/v1/executions/${executionId}/trace`))
      .pipe(catchError((e) => this.mapError(e)));
  }

  submitApproval(
    executionId: string,
    body: ApprovalSubmitBody,
  ): Observable<ApprovalCreatedResponse> {
    return this.http
      .post<ApprovalCreatedResponse>(this.url(`/v1/executions/${executionId}/approvals`), body)
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
