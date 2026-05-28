import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { API_BASE_URL } from './api-base-url.token';

/** Gateway runtime health — not under /v1. */
@Injectable({ providedIn: 'root' })
export class HealthApiService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);

  getRuntimeHealth(): Observable<Record<string, unknown>> {
    const root = this.base.replace(/\/$/, '');
    return this.http.get<Record<string, unknown>>(`${root}/health/runtime`);
  }
}
