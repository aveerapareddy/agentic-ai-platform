export interface PolicyRuleDescriptor {
  rule_id: string;
  description: string;
  applies_to: string[];
  decision: string;
  reason: string;
}

export interface PolicyListResponse {
  rule_pack_id: string;
  rules: PolicyRuleDescriptor[];
}

export interface PolicySimulateRequest {
  action_type: string;
  risk_level: string;
  execution_context: {
    environment: string;
    policy_scope: string;
  };
}

export interface PolicySimulateResponse {
  decision: string;
  reason: string;
  matched_rules: Record<string, unknown>[];
  rule_references: string[];
  rule_pack_id: string;
}
