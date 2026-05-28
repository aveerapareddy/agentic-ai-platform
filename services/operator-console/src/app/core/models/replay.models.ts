/** Replay and replay-diff shapes from api-gateway (orchestrator projections). */

export type ReplayMode = 'exact' | 'investigative';

/** Body for POST /v1/executions/{id}/replay (gateway ReplayExecutionRequest). */
export interface ReplayExecutionBody {
  mode: ReplayMode;
  environment_target: string;
  plan_id?: string | null;
  label?: string | null;
  reason?: string | null;
  requested_by?: string | null;
  input_overrides?: Record<string, unknown> | null;
  start_execution?: boolean;
}

export interface ReplayProvenanceDto {
  source_execution_id: string;
  replay_mode: ReplayMode;
  requested_by: string | null;
  reason: string | null;
  label: string | null;
  input_overrides: Record<string, unknown>;
  anchor_plan_id: string | null;
  environment_target: string;
  created_execution_id: string;
  created_at: string;
}

export interface ReplayCreatedResponseDto {
  replay_execution_id: string;
  source_execution_id: string;
  status: string;
  replay_mode: ReplayMode;
  provenance: ReplayProvenanceDto;
}

export type ReplayDiffSeverity = 'info' | 'warning' | 'significant';

export type ReplayDiffCategory =
  | 'lineage'
  | 'execution_status'
  | 'input'
  | 'plan'
  | 'step'
  | 'model_reasoning'
  | 'tool_call'
  | 'policy'
  | 'validation'
  | 'result';

export interface ReplayDiffItemDto {
  category: ReplayDiffCategory;
  severity: ReplayDiffSeverity;
  title: string;
  description: string;
  source_value: string | null;
  replay_value: string | null;
  path: string;
  related_step_id: string | null;
  related_tool_call_id: string | null;
}

export interface ReplayDiffSummaryDto {
  source_execution_id: string;
  replay_execution_id: string;
  replay_mode: ReplayMode | null;
  linked_to_source: boolean;
  total_differences: number;
  significant_differences: number;
  items: ReplayDiffItemDto[];
}
