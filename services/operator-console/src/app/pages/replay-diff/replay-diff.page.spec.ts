import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { of } from 'rxjs';
import { ReplayDiffPage } from './replay-diff.page';
import { ReplayApiService } from '../../core/api/replay-api.service';

describe('ReplayDiffPage', () => {
  let fixture: ComponentFixture<ReplayDiffPage>;
  let api: jasmine.SpyObj<ReplayApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('ReplayApiService', ['getReplayDiff']);
    api.getReplayDiff.and.returnValue(
      of({
        source_execution_id: 'src-1',
        replay_execution_id: 'rep-1',
        replay_mode: 'exact',
        linked_to_source: true,
        total_differences: 2,
        significant_differences: 1,
        items: [
          {
            category: 'lineage',
            severity: 'info',
            title: 'linked',
            description: 'd1',
            source_value: 'a',
            replay_value: 'b',
            path: 'lineage',
            related_step_id: null,
            related_tool_call_id: null,
          },
          {
            category: 'input',
            severity: 'warning',
            title: 'input.severity',
            description: 'd2',
            source_value: 'high',
            replay_value: 'low',
            path: 'input.severity',
            related_step_id: null,
            related_tool_call_id: null,
          },
        ],
      }),
    );
    await TestBed.configureTestingModule({
      imports: [ReplayDiffPage, RouterTestingModule],
      providers: [{ provide: ReplayApiService, useValue: api }],
    })
      .overrideComponent(ReplayDiffPage, {
        set: {
          providers: [
            {
              provide: ActivatedRoute,
              useValue: {
                paramMap: of(convertToParamMap({ sourceId: 'src-1', replayId: 'rep-1' })),
              },
            },
          ],
        },
      })
      .compileComponents();
    fixture = TestBed.createComponent(ReplayDiffPage);
  });

  it('groups diff items by category and renders severity', async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Replay diff');
    expect(el.textContent).toContain('lineage');
    expect(el.textContent).toContain('input');
    expect(el.textContent).toContain('Significant');
    expect(el.textContent).toContain('warning');
    expect(el.textContent).toContain('info');
    expect(fixture.componentInstance.grouped.length).toBe(2);
    expect(api.getReplayDiff).toHaveBeenCalledWith('src-1', 'rep-1');
  });
});
