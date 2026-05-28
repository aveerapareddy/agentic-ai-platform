import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { ExecutionReplayPanelComponent } from './execution-replay-panel.component';
import { ReplayApiService } from '../../core/api/replay-api.service';

describe('ExecutionReplayPanelComponent', () => {
  let fixture: ComponentFixture<ExecutionReplayPanelComponent>;
  let api: jasmine.SpyObj<ReplayApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('ReplayApiService', ['requestReplay']);
    await TestBed.configureTestingModule({
      imports: [ExecutionReplayPanelComponent],
      providers: [{ provide: ReplayApiService, useValue: api }, provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(ExecutionReplayPanelComponent);
    fixture.componentRef.setInput('execution', {
      execution_id: 'src-1',
      workflow_type: 'generic',
      status: 'completed',
      execution_context_id: 'c1',
      current_plan_id: null,
      parent_execution_id: null,
      input: {},
      result: null,
      validation_summary: null,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      completed_at: null,
      cancelled_at: null,
    });
  });

  it('renders replay section', () => {
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Replay');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Request replay');
  });

  it('shows JSON error for invalid investigative overrides', () => {
    fixture.detectChanges();
    const comp = fixture.componentInstance;
    comp.mode = 'investigative';
    comp.reason = 'hypothesis';
    comp.inputOverridesJson = '{not json';
    comp.submit();
    fixture.detectChanges();
    expect(comp.overrideJsonError).toContain('Invalid JSON');
    expect(api.requestReplay).not.toHaveBeenCalled();
  });

  it('requires reason or label for investigative mode', () => {
    fixture.detectChanges();
    const comp = fixture.componentInstance;
    comp.mode = 'investigative';
    comp.reason = '';
    comp.label = '';
    expect(comp.canSubmit).toBeFalse();
  });
});
