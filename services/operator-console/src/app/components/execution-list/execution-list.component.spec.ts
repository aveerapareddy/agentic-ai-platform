import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExecutionListComponent } from './execution-list.component';
import type { ExecutionListItem } from '../../core/models/execution.models';

describe('ExecutionListComponent', () => {
  let fixture: ComponentFixture<ExecutionListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExecutionListComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(ExecutionListComponent);
  });

  it('renders table rows when items exist', () => {
    fixture.componentRef.setInput('items', [
      {
        execution_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        status: 'completed',
        workflow_type: 'cost_attribution',
        created_at: '2026-01-02T00:00:00Z',
      } satisfies ExecutionListItem,
    ]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('cost attribution');
  });

  it('shows empty state when no items', () => {
    fixture.componentRef.setInput('items', []);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.oc-empty-state')).toBeTruthy();
  });
});
