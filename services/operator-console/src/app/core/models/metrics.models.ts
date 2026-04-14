/** Shapes aligned with api-gateway evaluation endpoints (evaluation-engine projections). */

export interface ExecutionMetricsDto {
  execution_id: string;
  workflow_type: string;
  execution_status: string;
  tenant_id: string | null;
  model_reasoning_event_count: number;
  model_reasoning_fallback_event_count: number;
  model_fallback_rate: number | null;
  validation_success: boolean | null;
  validation_detail: string | null;
  policy_decisions: string[];
  policy_outcome: string | null;
  tool_calls_total: number;
  tool_calls_success: number;
  tool_success_rate: number | null;
  step_latency_sum_ms: number | null;
  wall_clock_ms: number | null;
  total_latency_ms: number | null;
  computation_notes: string[];
}

export interface WorkflowTypeRollupDto {
  execution_count: number;
  failed_execution_count: number;
  mean_model_fallback_rate: number | null;
  mean_tool_success_rate: number | null;
  policy_decision_counts: Record<string, number>;
}

export interface StepTypeRollupDto {
  step_count: number;
  succeeded: number;
  failed: number;
  model_reasoning_events: number;
  model_fallback_events: number;
}

export interface ToolNameRollupDto {
  invocations: number;
  successes: number;
  failures: number;
}

export interface PolicyDecisionRollupDto {
  evaluation_count: number;
  distinct_execution_count: number;
}

export interface AggregatedMetricsDto {
  executions_in_scope: number;
  by_workflow_type: Record<string, WorkflowTypeRollupDto>;
  by_step_type: Record<string, StepTypeRollupDto>;
  by_tool_name: Record<string, ToolNameRollupDto>;
  by_policy_decision: Record<string, PolicyDecisionRollupDto>;
}
