from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from data.mock_questionnaire import questions
from src.graph.workflow import build_graph
from src.services.assessment_response import build_assessment_response

app = FastAPI(
    title="Client Assessment Agent API",
    description=(
        "API for extracting, verifying, and reconciling "
        "client assessment questionnaire responses."
    ),
    version="1.0.0",
)


class AssessmentRequest(BaseModel):
    case_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the assessment case.",
    )

    document_text: str = Field(
        ...,
        description="Text content of the client document.",
    )


def create_initial_state(case_id: str, document_text: str):
    return {
        "case_id": case_id,
        "document_text": document_text,
        "questions": questions,
        "ingestion_status": "",
        "extraction_status": "",
        "verification_status": "",
        "reconciliation_status": "",
        "workflow_status": "started",
        "extracted_data": {},
        "verification_results": {},
        "reconciliation_results": {},
        "question_results": {},
        "final_route": "",
        "errors": [],
        "audit_log": [],
    }


@app.get("/")
def root():
    return {
        "application": "Client Assessment Agent API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


@app.post("/assessments")
def create_assessment(request: AssessmentRequest):
    try:
        initial_state = create_initial_state(
            case_id=request.case_id,
            document_text=request.document_text,
        )

        graph = build_graph()
        final_state = graph.invoke(initial_state)

        response = build_assessment_response(final_state)

        return response.model_dump(mode="json")

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Assessment processing failed: {str(exc)}",
        ) from exc
