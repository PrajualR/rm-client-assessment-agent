from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


RouteType = Literal[
    "AUTO_FILL",
    "ESCALATE",
    "HUMAN_REVIEW",
]

VerificationStatus = Literal[
    "PASSED",
    "FAILED",
    "REVIEW_REQUIRED",
]

ExtractionStatus = Literal[
    "FOUND",
    "MISSING",
]


class QuestionnaireQuestion(BaseModel):
    question_id: str
    question: str
    field_name: str


class ExtractionResult(BaseModel):
    question_id: str
    field_name: str
    extracted_value: Any | None = None
    extraction_status: ExtractionStatus


class VerificationResult(BaseModel):
    field_name: str
    value: Any | None = None
    verification_status: VerificationStatus
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class ReconciliationResult(BaseModel):
    question_id: str
    field_name: str
    value: Any | None = None
    verification_status: VerificationStatus
    confidence: float = Field(ge=0.0, le=1.0)
    route: RouteType
    reason: str


class AuditEntry(BaseModel):
    timestamp: datetime
    agent: str
    action: str
    input: dict[str, Any]
    output: dict[str, Any]


class QuestionResult(BaseModel):
    question_id: str
    question: str
    field_name: str

    extracted_value: Any | None = None
    extraction_status: ExtractionStatus | None = None

    verification_status: VerificationStatus | None = None
    verification_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    verification_reason: str | None = None

    final_value: Any | None = None
    final_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    final_route: RouteType | None = None
    final_reason: str | None = None


class AssessmentError(BaseModel):
    timestamp: datetime
    agent: str
    error_type: str
    message: str


class AssessmentSummary(BaseModel):
    total_questions: int
    auto_fill_count: int
    escalation_count: int
    human_review_count: int
    answered_count: int
    missing_count: int


class AssessmentResponse(BaseModel):
    case_id: str
    workflow_status: str
    final_route: RouteType

    summary: AssessmentSummary
    question_results: list[QuestionResult]

    errors: list[AssessmentError]
    audit_log: list[AuditEntry]