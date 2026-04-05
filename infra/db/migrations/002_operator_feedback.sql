-- 002_operator_feedback.sql
-- Operator feedback distinct from Mukti execution_feedback; optional advisory score on Mukti rows.

CREATE TABLE IF NOT EXISTS operator_feedback (
    feedback_record_id UUID PRIMARY KEY,
    execution_id        UUID        NOT NULL
        REFERENCES executions (execution_id) ON DELETE CASCADE,
    source              TEXT        NOT NULL,
    labels              JSONB       NOT NULL DEFAULT '[]'::jsonb,
    detail              JSONB       NOT NULL DEFAULT '{}'::jsonb,
    source_scope        JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ,

    CONSTRAINT operator_feedback_source_chk
        CHECK (source IN ('operator_console', 'integration', 'api'))
);

CREATE INDEX IF NOT EXISTS idx_operator_feedback_execution_id
    ON operator_feedback (execution_id);

CREATE INDEX IF NOT EXISTS idx_operator_feedback_execution_id_created_at
    ON operator_feedback (execution_id, created_at DESC);

ALTER TABLE execution_feedback
    ADD COLUMN IF NOT EXISTS advisory_confidence NUMERIC;

COMMENT ON TABLE operator_feedback IS
    'Operator or integration-submitted feedback; distinct from post-execution Mukti execution_feedback.';
