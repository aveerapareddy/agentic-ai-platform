/** Mukti v2 cross-execution insights from GET /v1/insights/mukti (api-gateway). */

export type InsightSeverity = 'info' | 'warning' | 'elevated';

export type InsightCategory =
  | 'top_failure_type'
  | 'recurring_pattern'
  | 'policy_friction'
  | 'model_fallback'
  | 'unstable_workflow'
  | 'unstable_step'
  | 'improvement_suggestion';

export interface CrossExecutionInsightDto {
  insight_id: string;
  category: InsightCategory;
  severity: InsightSeverity;
  title: string;
  description: string;
  evidence_count: number;
  affected_workflows: string[];
  affected_steps: string[];
  suggested_action: string | null;
  related_execution_ids: string[];
  rank_score: number;
  evidence: Record<string, unknown>;
}

export interface RankedImprovementSuggestionDto {
  rank: number;
  category: string;
  summary: string;
  evidence_count: number;
  affected_workflows: string[];
  related_execution_ids: string[];
  suggested_action: string | null;
  detail: Record<string, unknown>;
}

export interface MuktiInsightsSummaryDto {
  scope_description: string;
  execution_feedback_sample_size: number;
  top_failure_types: CrossExecutionInsightDto[];
  recurring_patterns: CrossExecutionInsightDto[];
  policy_friction_areas: CrossExecutionInsightDto[];
  model_fallback_concentration: CrossExecutionInsightDto[];
  unstable_workflows_or_steps: CrossExecutionInsightDto[];
  ranked_improvement_suggestions: RankedImprovementSuggestionDto[];
  insights: CrossExecutionInsightDto[];
}
