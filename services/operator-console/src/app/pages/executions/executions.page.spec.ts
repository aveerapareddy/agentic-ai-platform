import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionListItem } from '../../core/models/execution.models';
import { ExecutionsPage } from './executions.page';

const SAMPLE: ExecutionListItem = {
  execution_id: '11111111-1111-4111-8111-111111111111',
  status: 'completed',
  workflow_type: 'incident_triage',
  created_at: '2026-01-01T00:00:00Z',
};

describe('ExecutionsPage', () => {
  let fixture: ComponentFixture<ExecutionsPage>;
  let api: jasmine.SpyObj<ExecutionApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj('ExecutionApiService', ['listExecutions']);
    await TestBed.configureTestingModule({
      imports: [ExecutionsPage],
      providers: [{ provide: ExecutionApiService, useValue: api }, provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(ExecutionsPage);
  });

  it('clears loading and renders rows on API success', () => {
    api.listExecutions.and.returnValue(of({ items: [SAMPLE], next_cursor: null }));
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(fixture.componentInstance.initialLoading).toBe(false);
    expect(fixture.componentInstance.loading).toBe(false);
    expect(el.textContent).toContain('incident_triage');
    expect(el.querySelector('.oc-skeleton')).toBeFalsy();
  });

  it('clears loading and shows error on API failure', () => {
    api.listExecutions.and.returnValue(throwError(() => new Error('gateway down')));
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(fixture.componentInstance.initialLoading).toBe(false);
    expect(fixture.componentInstance.loading).toBe(false);
    expect(el.textContent).toContain('gateway down');
    expect(el.querySelector('.oc-error')).toBeTruthy();
    expect(el.querySelector('.oc-skeleton')).toBeFalsy();
  });

  it('shows page header and filters while loading completes', () => {
    api.listExecutions.and.returnValue(of({ items: [], next_cursor: null }));
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Executions');
    expect(el.querySelector('.oc-filters')).toBeTruthy();
  });
});
