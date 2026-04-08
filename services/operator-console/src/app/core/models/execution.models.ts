/** Shapes aligned with api-gateway JSON (projections of platform records). */

export interface ExecutionListItem {
  execution_id: string;
  status: string;
  workflow_type: string;
  created_at: string;
}

export interface ListExecutionsResponse {
  items: ExecutionListItem[];
  next_cursor: string | null;
}

export interface ExecutionDetail {
  execution_id: string;
  workflow_type: string;
  status: string;
  execution_context_id: string;
  current_plan_id: string | null;
  parent_execution_id: string | null;
  input: Record<string, unknown>;
  result: Record<string, unknown> | null;
  validation_summary: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  cancelled_at: string | null;
}

export interface TraceView {
  execution_id: string;
  execution_context: Record<string, unknown>;
  plans: Record<string, unknown>[];
  steps: TraceStepRow[];
  tool_calls: Record<string, unknown>[];
  policy_evaluations: Record<string, unknown>[];
  approvals: Record<string, unknown>[];
  timeline: Record<string, unknown>[];
}

/** One row from gateway trace: `{ step, step_result }`. */
export interface TraceStepRow {
  step?: Record<string, unknown>;
  step_result?: Record<string, unknown> | null;
}

export interface ApprovalSubmitBody {
  action_proposal_id?: string | null;
  policy_evaluation_id?: string | null;
  decision: 'approve' | 'reject';
  approver: string;
  notes?: string | null;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    request_id?: string | null;
  };
}
