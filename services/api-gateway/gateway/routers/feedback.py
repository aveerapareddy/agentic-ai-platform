from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from gateway.dependencies import FeedbackFacadeDep
from gateway.http_errors import api_error
from gateway.schemas.requests import SubmitFeedbackRequest
from gateway.schemas.responses import FeedbackCreatedResponse

router = APIRouter(prefix="/executions", tags=["feedback"])


@router.post("/{execution_id}/feedback", status_code=201, response_model=FeedbackCreatedResponse)
def submit_feedback(
    execution_id: UUID,
    body: SubmitFeedbackRequest,
    request: Request,
    facade: FeedbackFacadeDep,
) -> FeedbackCreatedResponse:
    try:
        rec = facade.submit_feedback(
            execution_id,
            source=body.source,
            labels=body.labels,
            detail=body.detail,
            source_scope=body.source_scope,
        )
    except ValueError as e:
        raise api_error(code="VALIDATION_ERROR", message=str(e), status_code=400, request=request) from e

    return FeedbackCreatedResponse(
        feedback_record_id=rec.feedback_record_id,
        execution_id=rec.execution_id,
        created_at=rec.created_at,
    )
