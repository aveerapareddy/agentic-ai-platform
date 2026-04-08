import { SlicePipe } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import type { ExecutionListItem } from '../../core/models/execution.models';

@Component({
  selector: 'app-execution-list',
  standalone: true,
  imports: [SlicePipe],
  template: `
    @if (items.length === 0) {
      <p class="muted">No executions match the current filters.</p>
    } @else {
      <div class="table-wrap">
        <table class="data">
          <thead>
            <tr>
              <th>Execution ID</th>
              <th>Workflow</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            @for (row of items; track row.execution_id) {
              <tr class="clickable" (click)="select.emit(row.execution_id)" (keyup.enter)="select.emit(row.execution_id)" tabindex="0" role="button">
                <td class="mono">{{ row.execution_id }}</td>
                <td>{{ row.workflow_type }}</td>
                <td>
                  <span class="badge" [class]="row.status">{{ row.status }}</span>
                </td>
                <td class="muted">{{ row.created_at | slice: 0:19 }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
  styles: `
    .muted {
      color: var(--muted);
    }
  `,
})
export class ExecutionListComponent {
  @Input({ required: true }) items: ExecutionListItem[] = [];
  @Output() select = new EventEmitter<string>();
}
