import { Component, EventEmitter, Input, Output } from '@angular/core';
import type { ExecutionListItem } from '../../core/models/execution.models';
import { executionStatusModifier } from '../../core/ui/status-util';
import { formatIsoShort, shortExecutionId } from '../../core/ui/format-util';
import { workflowBadgeClass, workflowLabel } from '../../core/ui/workflow-util';

@Component({
  selector: 'app-execution-list',
  standalone: true,
  template: `
    @if (items.length === 0) {
      <div class="oc-empty-state">
        <p class="oc-empty-state__title">No executions in this view</p>
        <p class="oc-meta">Adjust filters or refresh after new runs complete on api-gateway.</p>
      </div>
    } @else {
      <div class="oc-table-wrap oc-exec-table">
        <table class="oc-table">
          <thead>
            <tr>
              <th class="col-id" scope="col">Execution</th>
              <th class="col-wf" scope="col">Workflow</th>
              <th class="col-st" scope="col">Status</th>
              <th class="col-ts" scope="col">Created</th>
              <th class="col-act" scope="col"><span class="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            @for (row of items; track row.execution_id) {
              <tr
                tabindex="0"
                [title]="row.execution_id + ' · ' + row.workflow_type + ' · ' + row.status"
                (click)="select.emit(row.execution_id)"
                (keyup.enter)="select.emit(row.execution_id)"
                (keyup.space)="$event.preventDefault(); select.emit(row.execution_id)"
              >
                <td class="col-id">
                  <span class="mono oc-exec-row__id">{{ shortId(row.execution_id) }}</span>
                </td>
                <td class="col-wf">
                  <span [class]="wfClass(row.workflow_type)">{{ wfLabel(row.workflow_type) }}</span>
                </td>
                <td class="col-st">
                  <span class="status-badge {{ statusClass(row.status) }}">{{ row.status }}</span>
                </td>
                <td class="col-ts oc-meta">{{ formatTs(row.created_at) }}</td>
                <td class="col-act oc-meta" aria-hidden="true">→</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <p class="oc-meta oc-table-foot">{{ items.length }} row(s) · click to open detail</p>
    }
  `,
  styles: ``,
})
export class ExecutionListComponent {
  @Input({ required: true }) items: ExecutionListItem[] = [];
  @Output() select = new EventEmitter<string>();

  shortId = shortExecutionId;
  formatTs = formatIsoShort;
  statusClass = executionStatusModifier;
  wfClass = workflowBadgeClass;
  wfLabel = workflowLabel;
}
