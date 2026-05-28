import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { API_BASE_URL } from './api-base-url.token';
import { InsightsApiService } from './insights-api.service';

describe('InsightsApiService', () => {
  let service: InsightsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [{ provide: API_BASE_URL, useValue: '' }],
    });
    service = TestBed.inject(InsightsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('GET /v1/insights/mukti', (done) => {
    service.getMuktiInsights({ tenant_id: 't1', limit: 25 }).subscribe((s) => {
      expect(s.execution_feedback_sample_size).toBe(1);
      expect(s.top_failure_types.length).toBe(1);
      done();
    });
    const req = http.expectOne(
      (r) =>
        r.url === '/v1/insights/mukti' &&
        r.params.get('tenant_id') === 't1' &&
        r.params.get('limit') === '25',
    );
    req.flush({
      scope_description: 'test',
      execution_feedback_sample_size: 1,
      top_failure_types: [
        {
          insight_id: '00000000-0000-4000-8000-000000000001',
          category: 'top_failure_type',
          severity: 'warning',
          title: 'step_failure',
          description: 'd',
          evidence_count: 2,
          affected_workflows: ['incident_triage'],
          affected_steps: [],
          suggested_action: 'act',
          related_execution_ids: [],
          rank_score: 20,
          evidence: {},
        },
      ],
      recurring_patterns: [],
      policy_friction_areas: [],
      model_fallback_concentration: [],
      unstable_workflows_or_steps: [],
      ranked_improvement_suggestions: [],
      insights: [],
    });
  });
});
