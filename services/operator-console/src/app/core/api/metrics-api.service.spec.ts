import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { API_BASE_URL } from './api-base-url.token';
import { MetricsApiService } from './metrics-api.service';

describe('MetricsApiService', () => {
  let service: MetricsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [{ provide: API_BASE_URL, useValue: '' }],
    });
    service = TestBed.inject(MetricsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('GET /v1/executions/:id/metrics', (done) => {
    service.getExecutionMetrics('e1').subscribe((m) => {
      expect(m.workflow_type).toBe('generic');
      expect(m.policy_outcome).toBe('allow');
      done();
    });
    const req = http.expectOne('/v1/executions/e1/metrics');
    expect(req.request.method).toBe('GET');
    req.flush({
      execution_id: 'e1',
      workflow_type: 'generic',
      execution_status: 'completed',
      tenant_id: 't1',
      model_reasoning_event_count: 0,
      model_reasoning_fallback_event_count: 0,
      model_fallback_rate: null,
      validation_success: null,
      validation_detail: null,
      policy_decisions: ['allow'],
      policy_outcome: 'allow',
      tool_calls_total: 0,
      tool_calls_success: 0,
      tool_success_rate: null,
      step_latency_sum_ms: null,
      wall_clock_ms: null,
      total_latency_ms: null,
      computation_notes: [],
    });
  });

  it('GET /v1/metrics with query params', (done) => {
    service.getAggregatedMetrics({ tenant_id: 't1', limit: 50 }).subscribe((agg) => {
      expect(agg.executions_in_scope).toBe(2);
      done();
    });
    const req = http.expectOne(
      (r) => r.url === '/v1/metrics' && r.params.get('tenant_id') === 't1' && r.params.get('limit') === '50',
    );
    expect(req.request.method).toBe('GET');
    req.flush({
      executions_in_scope: 2,
      by_workflow_type: {},
      by_step_type: {},
      by_tool_name: {},
      by_policy_decision: {},
    });
  });
});
