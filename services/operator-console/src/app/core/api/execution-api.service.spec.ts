import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { API_BASE_URL } from './api-base-url.token';
import { ExecutionApiService } from './execution-api.service';

describe('ExecutionApiService', () => {
  let service: ExecutionApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [{ provide: API_BASE_URL, useValue: '' }],
    });
    service = TestBed.inject(ExecutionApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('GET /v1/executions with query params', (done) => {
    service
      .listExecutions({ tenant_id: 't1', workflow_type: 'incident_triage', limit: 10 })
      .subscribe((res) => {
        expect(res.items.length).toBe(1);
        done();
      });
    const req = http.expectOne(
      (r) =>
        r.url === '/v1/executions' &&
        r.params.get('tenant_id') === 't1' &&
        r.params.get('workflow_type') === 'incident_triage' &&
        r.params.get('limit') === '10',
    );
    expect(req.request.method).toBe('GET');
    req.flush({ items: [{ execution_id: 'x', status: 'created', workflow_type: 'incident_triage', created_at: '2026-01-01' }], next_cursor: null });
  });

  it('POST approval forwards body shape', (done) => {
    service
      .submitApproval('e1', {
        action_proposal_id: 'p1',
        policy_evaluation_id: 'v1',
        decision: 'approve',
        approver: 'op',
        notes: null,
      })
      .subscribe((res) => {
        expect(res.decision).toBe('approve');
        done();
      });
    const req = http.expectOne('/v1/executions/e1/approvals');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.approver).toBe('op');
    req.flush({
      approval_id: 'a1',
      execution_id: 'e1',
      decision: 'approve',
      decided_at: '2026-01-01T00:00:00Z',
    });
  });
});
