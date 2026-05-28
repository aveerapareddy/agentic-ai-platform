import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { API_BASE_URL } from './api-base-url.token';
import { ReplayApiService } from './replay-api.service';

describe('ReplayApiService', () => {
  let service: ReplayApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [{ provide: API_BASE_URL, useValue: '' }],
    });
    service = TestBed.inject(ReplayApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('POST /v1/executions/:id/replay', (done) => {
    service
      .requestReplay('src-1', {
        mode: 'investigative',
        environment_target: 'sandbox',
        reason: 'test',
        input_overrides: { severity: 'low' },
      })
      .subscribe((res) => {
        expect(res.replay_execution_id).toBe('rep-1');
        expect(res.replay_mode).toBe('investigative');
        done();
      });
    const req = http.expectOne('/v1/executions/src-1/replay');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.mode).toBe('investigative');
    req.flush({
      replay_execution_id: 'rep-1',
      source_execution_id: 'src-1',
      status: 'created',
      replay_mode: 'investigative',
      provenance: {
        source_execution_id: 'src-1',
        replay_mode: 'investigative',
        requested_by: null,
        reason: 'test',
        label: null,
        input_overrides: { severity: 'low' },
        anchor_plan_id: null,
        environment_target: 'sandbox',
        created_execution_id: 'rep-1',
        created_at: '2026-01-01T00:00:00Z',
      },
    });
  });

  it('GET /v1/executions/:source/replay-diff/:replay', (done) => {
    service.getReplayDiff('src-1', 'rep-1').subscribe((s) => {
      expect(s.linked_to_source).toBe(true);
      expect(s.items.length).toBe(1);
      done();
    });
    const req = http.expectOne('/v1/executions/src-1/replay-diff/rep-1');
    expect(req.request.method).toBe('GET');
    req.flush({
      source_execution_id: 'src-1',
      replay_execution_id: 'rep-1',
      replay_mode: 'exact',
      linked_to_source: true,
      total_differences: 1,
      significant_differences: 0,
      items: [
        {
          category: 'lineage',
          severity: 'info',
          title: 'linked_to_source',
          description: 'ok',
          source_value: 'src-1',
          replay_value: 'src-1',
          path: 'lineage',
          related_step_id: null,
          related_tool_call_id: null,
        },
      ],
    });
  });
});
