/** SSE execution stream events from GET /v1/executions/{id}/stream */

export type ExecutionStreamEventType =
  | 'execution_updated'
  | 'step_updated'
  | 'trace_event'
  | 'approval_required'
  | 'execution_completed'
  | 'execution_failed'
  | 'execution_cancelled'
  | 'replay_created'
  | 'heartbeat';

export interface ExecutionStreamEvent {
  event_type: ExecutionStreamEventType;
  execution_id: string;
  sequence: number;
  emitted_at: string;
  payload: Record<string, unknown>;
}

export const TERMINAL_STREAM_EVENTS: ReadonlySet<ExecutionStreamEventType> = new Set([
  'execution_completed',
  'execution_failed',
  'execution_cancelled',
]);

export function isTerminalStreamEvent(type: ExecutionStreamEventType): boolean {
  return TERMINAL_STREAM_EVENTS.has(type);
}

export function isTerminalExecutionStatus(status: string): boolean {
  return status === 'completed' || status === 'failed' || status === 'cancelled';
}
