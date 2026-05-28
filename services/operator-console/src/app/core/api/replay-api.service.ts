import { HttpClient } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE_URL } from './api-base-url.token';
import type { ApiErrorBody } from '../models/execution.models';
import type { ReplayCreatedResponseDto, ReplayDiffSummaryDto, ReplayExecutionBody } from '../models/replay.models';

@Injectable({ providedIn: 'root' })
export class ReplayApiService {
  constructor(
    private readonly http: HttpClient,
    @Inject(API_BASE_URL) private readonly baseUrl: string,
  ) {}

  private url(path: string): string {
    const base = this.baseUrl.replace(/\/$/, '');
    return `${base}${path}`;
  }

  requestReplay(executionId: string, body: ReplayExecutionBody): Observable<ReplayCreatedResponseDto> {
    return this.http
      .post<ReplayCreatedResponseDto>(this.url(`/v1/executions/${executionId}/replay`), body)
      .pipe(catchError((e) => this.mapError(e)));
  }

  getReplayDiff(sourceExecutionId: string, replayExecutionId: string): Observable<ReplayDiffSummaryDto> {
    return this.http
      .get<ReplayDiffSummaryDto>(
        this.url(`/v1/executions/${sourceExecutionId}/replay-diff/${replayExecutionId}`),
      )
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
