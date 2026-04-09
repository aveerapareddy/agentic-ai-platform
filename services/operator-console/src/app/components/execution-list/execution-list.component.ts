import { Component, EventEmitter, Input, Output } from '@angular/core';
import type { ExecutionListItem } from '../../core/models/execution.models';
import { executionStatusModifier } from '../../core/ui/status-util';
import { formatIsoShort, shortExecutionId } from '../../core/ui/format-util';

@Component({
  selector: 'app-execution-list',
  standalone: true,
  template: `
    @if (items.length === 0) {
      <div class="oc-panel">
        <p class="oc-meta oc-empty">No executions match the current filters.</p>
      </div>
    } @else {
      <div class="oc-table-wrap">
        <table class="oc-table">
          <thead>
            <tr>
              <th class="col-id" scope="col">Execution</th>
              <th class="col-wf" scope="col">Workflow</th>
              <th class="col-st" scope="col">Status</th>
              <th class="col-ts" scope="col">Created</th>
            </tr>
          </thead>
          <tbody>
            @for (row of items; track row.execution_id) {
              <tr
                tabindex="0"
                (click)="select.emit(row.execution_id)"
                (keyup.enter)="select.emit(row.execution_id)"
                (keyup.space)="$event.preventDefault(); select.emit(row.execution_id)"
              >
                <td class="col-id mono" [title]="row.execution_id">{{ shortId(row.execution_id) }}</td>
                <td class="col-wf oc-data">{{ row.workflow_type }}</td>
                <td class="col-st">
                  <span class="status-badge {{ statusClass(row.status) }}">{{ row.status }}</span>
                </td>
                <td class="col-ts">{{ formatTs(row.created_at) }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
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
}
