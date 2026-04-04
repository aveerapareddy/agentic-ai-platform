"""Typed UUID aliases for cross-service readability (no runtime distinction from UUID)."""

from __future__ import annotations

from typing import TypeAlias
from uuid import UUID

ActionId: TypeAlias = UUID
"""Action proposal identifier (maps to `proposal_id` in persistence)."""

ApprovalId: TypeAlias = UUID
ContextId: TypeAlias = UUID
ExecutionId: TypeAlias = UUID
FeedbackId: TypeAlias = UUID
PlanId: TypeAlias = UUID
PolicyEvaluationId: TypeAlias = UUID
ResultId: TypeAlias = UUID
RetrievalId: TypeAlias = UUID
"""Correlation id for a single knowledge-service retrieval response."""

StepId: TypeAlias = UUID
ToolCallId: TypeAlias = UUID
