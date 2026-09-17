from src.models.assessment_models import (AssessmentError, AssessmentResponse,
                                          AssessmentSummary, AuditEntry,
                                          QuestionResult)


def build_assessment_response(state):
    question_results = [
        QuestionResult(**question_result)
        for question_result in state.get(
            "question_results",
            {},
        ).values()
    ]

    reconciliation_results = state.get(
        "reconciliation_results",
        {},
    )

    route_counts = {
        "AUTO_FILL": 0,
        "ESCALATE": 0,
        "HUMAN_REVIEW": 0,
    }

    for result in reconciliation_results.values():
        route = result["route"]

        if route in route_counts:
            route_counts[route] += 1

    answered_count = sum(
        1 for result in question_results if result.extracted_value is not None
    )

    missing_count = len(question_results) - answered_count

    summary = AssessmentSummary(
        total_questions=len(question_results),
        auto_fill_count=route_counts["AUTO_FILL"],
        escalation_count=route_counts["ESCALATE"],
        human_review_count=route_counts["HUMAN_REVIEW"],
        answered_count=answered_count,
        missing_count=missing_count,
    )

    errors = [AssessmentError(**error) for error in state.get("errors", [])]

    audit_log = [AuditEntry(**entry) for entry in state.get("audit_log", [])]

    return AssessmentResponse(
        case_id=state["case_id"],
        workflow_status=state["workflow_status"],
        final_route=state["final_route"],
        summary=summary,
        question_results=question_results,
        errors=errors,
        audit_log=audit_log,
    )
