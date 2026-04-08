import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { ApprovalPanelComponent } from './approval-panel.component';
import { ExecutionApiService } from '../../core/api/execution-api.service';
import type { ExecutionDetail } from '../../core/models/execution.models';

describe('ApprovalPanelComponent', () => {
  let fixture: ComponentFixture<ApprovalPanelComponent>;
  let api: jasmine.SpyObj<ExecutionApiService>;

  const awaiting: ExecutionDetail = {
    execution_id: '00000000-0000-4000-8000-000000000099',
    workflow_type: 'incident_triage',
    status: 'awaiting_approval',
    execution_context_id: '00000000-0000-4000-8000-000000000088',
    current_plan_id: null,
    parent_execution_id: null,
    input: {},
    result: {
      governance: {
        proposal_id: '00000000-0000-4000-8000-0000000000aa',
        evaluation_id: '00000000-0000-4000-8000-0000000000bb',
      },
    },
    validation_summary: null,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
    completed_at: null,
    cancelled_at: null,
  };

  beforeEach(async () => {
    api = jasmine.createSpyObj('ExecutionApiService', ['submitApproval']);
    await TestBed.configureTestingModule({
      imports: [ApprovalPanelComponent, FormsModule],
      providers: [{ provide: ExecutionApiService, useValue: api }],
    }).compileComponents();
    fixture = TestBed.createComponent(ApprovalPanelComponent);
  });

  it('renders panel when status is awaiting_approval', () => {
    fixture.componentInstance.execution = awaiting;
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Approval');
    expect(el.textContent).toContain('awaiting_approval');
  });

  it('does not render when not awaiting approval', () => {
    fixture.componentInstance.execution = { ...awaiting, status: 'completed' };
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.panel.approval')).toBeNull();
  });

  it('calls API on approve and emits decided', (done) => {
    api.submitApproval.and.returnValue(
      of({
        approval_id: 'a',
        execution_id: awaiting.execution_id,
        decision: 'approve',
        decided_at: '2026-01-01',
      }),
    );
    fixture.componentInstance.execution = awaiting;
    fixture.componentInstance.approver = 'tester';
    fixture.detectChanges();

    fixture.componentInstance.decided.subscribe(() => {
      expect(api.submitApproval).toHaveBeenCalled();
      done();
    });
    fixture.componentInstance.submit('approve');
  });

  it('surfaces API errors', () => {
    api.submitApproval.and.returnValue(throwError(() => new Error('CONFLICT')));
    fixture.componentInstance.execution = awaiting;
    fixture.componentInstance.approver = 'tester';
    fixture.detectChanges();
    fixture.componentInstance.submit('reject');
    expect(fixture.componentInstance.error).toContain('CONFLICT');
  });
});
