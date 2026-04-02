-- 001_initial_schema.sql
-- Runtime-aligned operational schema (PostgreSQL).
-- Idempotent: CREATE IF NOT EXISTS for tables and indexes.
--
-- Trace: there is no dedicated `traces` table; the trace is reconstructed from
-- executions (timeline/summary JSONB), execution_steps, step_results, tool_calls,
-- policy_evaluations, and approvals. Normalized rows stay queryable and FK-linked
-- for replay and operator views without duplicating a monolithic trace blob.

-- =============================================================================
-- execution_context
-- =============================================================================
CREATE TABLE IF NOT EXISTS execution_context (
    context_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           TEXT        NOT NULL,
    principal_id        TEXT,
    actor               TEXT,
    request_id          TEXT        NOT NULL,
    environment         TEXT        NOT NULL,
    permissions_scope   JSONB       NOT NULL DEFAULT '{}'::jsonb,
    policy_scope        TEXT        NOT NULL,
    feature_flags       JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_execution_context_tenant_id
    ON execution_context (tenant_id);

CREATE INDEX IF NOT EXISTS idx_execution_context_request_id
    ON execution_context (request_id);

-- =============================================================================
-- executions
-- =============================================================================
CREATE TABLE IF NOT EXISTS executions (
    execution_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_type        TEXT        NOT NULL,
    status               TEXT        NOT NULL,
    execution_context_id UUID        NOT NULL
        REFERENCES execution_context (context_id) ON DELETE RESTRICT,
    parent_execution_id  UUID
        REFERENCES executions (execution_id) ON DELETE SET NULL,
    current_plan_id      UUID,
    input                JSONB       NOT NULL DEFAULT '{}'::jsonb,
    result               JSONB,
    trace_timeline       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    validation_summary   JSONB,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ,
    cancelled_at         TIMESTAMPTZ,

    CONSTRAINT executions_status_chk
        CHECK (status IN (
            'created',
            'planning',
            'executing',
            'validating',
            'awaiting_approval',
            'completed',
            'failed',
            'cancelled'
        ))
);

-- One execution row per context row (1:1 for tenant isolation and audit).
CREATE UNIQUE INDEX IF NOT EXISTS idx_executions_execution_context_id_uniq
    ON executions (execution_context_id);

CREATE INDEX IF NOT EXISTS idx_executions_parent_id
    ON executions (parent_execution_id);

CREATE INDEX IF NOT EXISTS idx_executions_status
    ON executions (status);

CREATE INDEX IF NOT EXISTS idx_executions_workflow_type
    ON executions (workflow_type);

CREATE INDEX IF NOT EXISTS idx_executions_created_at
    ON executions (created_at DESC);

-- =============================================================================
-- execution_plans
-- =============================================================================
CREATE TABLE IF NOT EXISTS execution_plans (
    plan_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id     UUID        NOT NULL
        REFERENCES executions (execution_id) ON DELETE CASCADE,
    parent_plan_id   UUID
        REFERENCES execution_plans (plan_id) ON DELETE SET NULL,
    plan_version     INTEGER     NOT NULL,
    revision_reason  TEXT,
    goal             JSONB       NOT NULL DEFAULT '{}'::jsonb,
    steps            JSONB       NOT NULL DEFAULT '[]'::jsonb,
    dependencies     JSONB       NOT NULL DEFAULT '[]'::jsonb,
    ordering         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    metadata         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT execution_plans_version_positive_chk
        CHECK (plan_version > 0),
    CONSTRAINT execution_plans_version_per_execution_uniq
        UNIQUE (execution_id, plan_version)
);

CREATE INDEX IF NOT EXISTS idx_execution_plans_execution_id
    ON execution_plans (execution_id);

CREATE INDEX IF NOT EXISTS idx_execution_plans_execution_id_version_desc
    ON execution_plans (execution_id, plan_version DESC);

CREATE INDEX IF NOT EXISTS idx_execution_plans_parent_plan_id
    ON execution_plans (parent_plan_id);

-- Point executions.current_plan_id at the active plan revision (FK added after both tables exist).
ALTER TABLE executions
    DROP CONSTRAINT IF EXISTS executions_current_plan_id_fkey;

ALTER TABLE executions
    ADD CONSTRAINT executions_current_plan_id_fkey
        FOREIGN KEY (current_plan_id)
        REFERENCES execution_plans (plan_id)
        ON DELETE SET NULL;

-- =============================================================================
-- execution_steps
-- =============================================================================
CREATE TABLE IF NOT EXISTS execution_steps (
    step_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id     UUID        NOT NULL
        REFERENCES executions (execution_id) ON DELETE CASCADE,
    plan_id          UUID        NOT NULL
        REFERENCES execution_plans (plan_id) ON DELETE RESTRICT,
    type             TEXT        NOT NULL,
    agent            TEXT        NOT NULL,
    input            JSONB       NOT NULL DEFAULT '{}'::jsonb,
    status           TEXT        NOT NULL,
    dependencies     JSONB       NOT NULL DEFAULT '[]'::jsonb,
    retry_count      INTEGER     NOT NULL DEFAULT 0,
    degraded_allowed BOOLEAN     NOT NULL DEFAULT false,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT execution_steps_status_chk
        CHECK (status IN (
            'pending',
            'running',
            'succeeded',
            'failed',
            'skipped',
            'cancelled'
        )),
    CONSTRAINT execution_steps_retry_count_chk
        CHECK (retry_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_execution_steps_execution_id
    ON execution_steps (execution_id);

CREATE INDEX IF NOT EXISTS idx_execution_steps_plan_id
    ON execution_steps (plan_id);

CREATE INDEX IF NOT EXISTS idx_execution_steps_execution_status
    ON execution_steps (execution_id, status);

CREATE INDEX IF NOT EXISTS idx_execution_steps_execution_id_created_at
    ON execution_steps (execution_id, created_at);

-- =============================================================================
-- step_results (1:1 with execution_steps)
-- =============================================================================
CREATE TABLE IF NOT EXISTS step_results (
    step_result_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id           UUID        NOT NULL
        REFERENCES execution_steps (step_id) ON DELETE CASCADE,
    output            JSONB,
    evidence          JSONB       NOT NULL DEFAULT '[]'::jsonb,
    errors            JSONB       NOT NULL DEFAULT '[]'::jsonb,
    latency_ms        INTEGER,
    latency_started_at TIMESTAMPTZ,
    latency_ended_at   TIMESTAMPTZ,
    confidence_score  NUMERIC,
    confidence_detail JSONB,
    completeness      TEXT,
    validation_outcome JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT step_results_step_id_uniq
        UNIQUE (step_id),
    CONSTRAINT step_results_completeness_chk
        CHECK (
            completeness IS NULL
            OR completeness IN ('full', 'partial', 'degraded')
        ),
    CONSTRAINT step_results_latency_ms_chk
        CHECK (latency_ms IS NULL OR latency_ms >= 0),
    CONSTRAINT step_results_confidence_score_chk
        CHECK (
            confidence_score IS NULL
            OR (confidence_score >= 0 AND confidence_score <= 1)
        )
);

CREATE INDEX IF NOT EXISTS idx_step_results_step_id
    ON step_results (step_id);

CREATE INDEX IF NOT EXISTS idx_step_results_confidence_score
    ON step_results (confidence_score)
    WHERE confidence_score IS NOT NULL;

-- =============================================================================
-- action_proposals
-- =============================================================================
CREATE TABLE IF NOT EXISTS action_proposals (
    proposal_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id       UUID        NOT NULL
        REFERENCES executions (execution_id) ON DELETE CASCADE,
    step_id            UUID
        REFERENCES execution_steps (step_id) ON DELETE SET NULL,
    action_type        TEXT        NOT NULL,
    payload            JSONB       NOT NULL DEFAULT '{}'::jsonb,
    risk_level         TEXT        NOT NULL,
    requires_approval  BOOLEAN     NOT NULL DEFAULT false,
    status             TEXT        NOT NULL DEFAULT 'proposed',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT action_proposals_risk_level_chk
        CHECK (risk_level IN ('low', 'medium', 'high')),
    CONSTRAINT action_proposals_status_chk
        CHECK (status IN (
            'proposed',
            'policy_denied',
            'awaiting_approval',
            'approved',
            'rejected',
            'executed',
            'failed'
        ))
);

CREATE INDEX IF NOT EXISTS idx_action_proposals_execution_id
    ON action_proposals (execution_id);

CREATE INDEX IF NOT EXISTS idx_action_proposals_step_id
    ON action_proposals (step_id);

CREATE INDEX IF NOT EXISTS idx_action_proposals_execution_id_created_at
    ON action_proposals (execution_id, created_at);

-- =============================================================================
-- tool_calls
-- =============================================================================
CREATE TABLE IF NOT EXISTS tool_calls (
    tool_call_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id           UUID        NOT NULL
        REFERENCES executions (execution_id) ON DELETE CASCADE,
    step_id                UUID        NOT NULL
        REFERENCES execution_steps (step_id) ON DELETE CASCADE,
    execution_context_id   UUID        NOT NULL
        REFERENCES execution_context (context_id) ON DELETE RESTRICT,
    action_proposal_id     UUID
        REFERENCES action_proposals (proposal_id) ON DELETE SET NULL,
    tool_name              TEXT        NOT NULL,
    side_effect_class      TEXT        NOT NULL,
    idempotency            TEXT        NOT NULL,
    input                  JSONB       NOT NULL DEFAULT '{}'::jsonb,
    output                 JSONB,
    status                 TEXT        NOT NULL,
    latency_ms             INTEGER,
    error                  JSONB,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT tool_calls_status_chk
        CHECK (status IN ('success', 'failure', 'timeout', 'rejected_by_policy')),
    CONSTRAINT tool_calls_side_effect_chk
        CHECK (side_effect_class IN ('read_only', 'state_changing')),
    CONSTRAINT tool_calls_idempotency_chk
        CHECK (idempotency IN ('idempotent', 'non_idempotent')),
    CONSTRAINT tool_calls_latency_ms_nonnegative_chk
        CHECK (latency_ms IS NULL OR latency_ms >= 0)
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_execution_id
    ON tool_calls (execution_id);

CREATE INDEX IF NOT EXISTS idx_tool_calls_step_id
    ON tool_calls (step_id);

CREATE INDEX IF NOT EXISTS idx_tool_calls_context_id
    ON tool_calls (execution_context_id);

CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_name
    ON tool_calls (tool_name);

CREATE INDEX IF NOT EXISTS idx_tool_calls_created_at
    ON tool_calls (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tool_calls_execution_id_created_at
    ON tool_calls (execution_id, created_at);

-- =============================================================================
-- policy_evaluations
-- =============================================================================
CREATE TABLE IF NOT EXISTS policy_evaluations (
    evaluation_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id        UUID        NOT NULL
        REFERENCES executions (execution_id) ON DELETE CASCADE,
    execution_context_id UUID       NOT NULL
        REFERENCES execution_context (context_id) ON DELETE RESTRICT,
    decision            TEXT        NOT NULL,
    reason              TEXT        NOT NULL,
    evaluated_rules     JSONB       NOT NULL DEFAULT '[]'::jsonb,
    subject_ref         JSONB       NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT policy_evaluations_decision_chk
        CHECK (decision IN ('allow', 'deny', 'conditional'))
);

CREATE INDEX IF NOT EXISTS idx_policy_evaluations_execution_id
    ON policy_evaluations (execution_id);

CREATE INDEX IF NOT EXISTS idx_policy_evaluations_execution_id_created_at
    ON policy_evaluations (execution_id, created_at DESC);

-- =============================================================================
-- approvals
-- =============================================================================
CREATE TABLE IF NOT EXISTS approvals (
    approval_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id          UUID        NOT NULL
        REFERENCES executions (execution_id) ON DELETE CASCADE,
    policy_evaluation_id  UUID
        REFERENCES policy_evaluations (evaluation_id) ON DELETE SET NULL,
    action_proposal_id    UUID
        REFERENCES action_proposals (proposal_id) ON DELETE SET NULL,
    approver              TEXT        NOT NULL,
    decision              TEXT        NOT NULL,
    notes                 TEXT,
    decided_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT approvals_decision_chk
        CHECK (decision IN ('approve', 'reject', 'defer')),
    CONSTRAINT approvals_subject_chk
        CHECK (
            policy_evaluation_id IS NOT NULL
            OR action_proposal_id IS NOT NULL
        )
);

CREATE INDEX IF NOT EXISTS idx_approvals_execution_id
    ON approvals (execution_id);

CREATE INDEX IF NOT EXISTS idx_approvals_proposal_id
    ON approvals (action_proposal_id);

CREATE INDEX IF NOT EXISTS idx_approvals_policy_evaluation_id
    ON approvals (policy_evaluation_id);

CREATE INDEX IF NOT EXISTS idx_approvals_execution_id_created_at
    ON approvals (execution_id, created_at);

-- =============================================================================
-- execution_feedback (Mukti, post-execution)
-- =============================================================================
CREATE TABLE IF NOT EXISTS execution_feedback (
    feedback_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id            UUID        NOT NULL
        REFERENCES executions (execution_id) ON DELETE CASCADE,
    source_scope            JSONB,
    failure_types           JSONB       NOT NULL DEFAULT '[]'::jsonb,
    patterns_detected       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    improvement_suggestions JSONB      NOT NULL DEFAULT '[]'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_execution_feedback_execution_id
    ON execution_feedback (execution_id);

CREATE INDEX IF NOT EXISTS idx_execution_feedback_created_at
    ON execution_feedback (created_at DESC);

-- =============================================================================
-- Documentation (COMMENT ON is idempotent: last write wins)
-- =============================================================================
COMMENT ON TABLE execution_plans IS
    'Immutable plan revisions per execution. parent_plan_id + plan_version preserve lineage; '
    'executions.current_plan_id points at the active revision for scheduling while history remains queryable.';

COMMENT ON COLUMN executions.current_plan_id IS
    'FK to the plan revision currently driving step scheduling; superseded revisions stay in execution_plans for audit and replay.';

COMMENT ON COLUMN executions.input IS
    'Workflow-typed initial payload (JSONB) to avoid rigid schema migrations for evolving workflow inputs.';

COMMENT ON COLUMN executions.trace_timeline IS
    'Optional ordered event stream; authoritative detail still lives in normalized step/tool/policy rows.';

COMMENT ON COLUMN executions.result IS
    'Terminal aggregated outcome JSONB when execution completes; complements per-step step_results.';

COMMENT ON COLUMN execution_context.permissions_scope IS
    'Entitlements snapshot as JSONB; structure evolves with IAM without ALTER TABLE churn.';

COMMENT ON COLUMN execution_context.feature_flags IS
    'Active toggles affecting branching; must align with trace when they influence outcomes (runtime model).';

COMMENT ON COLUMN step_results.output IS
    'Structured step output; JSONB accommodates workflow-specific shapes.';

COMMENT ON COLUMN step_results.evidence IS
    'Citations, retrieval pointers, excerpts (JSONB) for traceable grounding; schema varies by workflow.';

COMMENT ON COLUMN step_results.confidence_score IS
    'Optional scalar in [0,1] for filtering and dashboards; advisory only—validation outcomes govern promotion.';

COMMENT ON COLUMN step_results.confidence_detail IS
    'Non-scalar calibration metadata (model id, rationale, ordinal labels) complementing confidence_score.';

COMMENT ON COLUMN action_proposals.payload IS
    'Action parameters as JSONB; validated at application/policy boundary per action_type.';

COMMENT ON COLUMN policy_evaluations.subject_ref IS
    'Opaque reference to evaluated subject {type, id, ...}; JSONB avoids polymorphic FK proliferation.';

COMMENT ON TABLE execution_feedback IS
    'Post-execution Mukti analysis; advisory only, does not mutate live execution rows.';
