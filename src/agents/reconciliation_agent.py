from datetime import datetime, timezone

from src.config.settings import settings
from src.models.assessment_models import ReconciliationResult
from src.utils.question_helpers import get_question_value


def determine_route(confidence: float) -> str:
    if confidence >= settings.auto_fill_threshold:
        return "AUTO_FILL"

    if confidence >= settings.escalation_threshold:
        return "ESCALATE"

    return "HUMAN_REVIEW"


def reconciliation_agent(state):
    """
    Reconcile extracted and verified values for every question.
    """

    try:
        question_results = dict(state.get("question_results", {}))
        reconciliation_results = {}

        for question in state["questions"]:
            question_id = get_question_value(question, "question_id")
            field_name = get_question_value(question, "field_name")

            question_result = question_results.get(question_id, {})

            extracted_value = question_result.get("extracted_value")
            extraction_status = question_result.get("extraction_status")

            verification_status = question_result.get(
                "verification_status"
            )

            verification_confidence = question_result.get(
                "verification_confidence"
            )

            verification_reason = question_result.get(
                "verification_reason"
            )

            if extraction_status == "MISSING":
                confidence = 0.0
                route = "HUMAN_REVIEW"
                reason = "Required answer was not found in the document."

            elif verification_confidence is None:
                confidence = 0.0
                route = "HUMAN_REVIEW"
                reason = "Verification result is unavailable."

            else:
                confidence = verification_confidence
                route = determine_route(confidence)
                reason = (
                    verification_reason
                    or "Reconciliation completed."
                )

            reconciliation_result = ReconciliationResult(
                question_id=question_id,
                field_name=field_name,
                value=extracted_value,
                verification_status=(
                    verification_status or "REVIEW_REQUIRED"
                ),
                confidence=confidence,
                route=route,
                reason=reason,
            )

            reconciliation_results[question_id] = (
                reconciliation_result.model_dump()
            )

            question_results[question_id] = {
                **question_result,
                "final_value": extracted_value,
                "final_confidence": confidence,
                "final_route": route,
                "final_reason": reason,
            }

        routes = [
            result["route"]
            for result in reconciliation_results.values()
        ]

        if "HUMAN_REVIEW" in routes:
            final_route = "HUMAN_REVIEW"
        elif "ESCALATE" in routes:
            final_route = "ESCALATE"
        else:
            final_route = "AUTO_FILL"

        audit_log = list(state.get("audit_log", []))

        audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "agent": "ReconciliationAgent",
                "action": "Reconciled questionnaire answers",
                "input": {
                    "question_count": len(state["questions"]),
                },
                "output": {
                    "reconciliation_status": "success",
                    "final_route": final_route,
                    "question_count": len(reconciliation_results),
                },
            }
        )

        return {
            **state,
            "reconciliation_status": "success",
            "reconciliation_results": reconciliation_results,
            "question_results": question_results,
            "final_route": final_route,
            "audit_log": audit_log,
        }

    except Exception as exc:
        errors = list(state.get("errors", []))
        audit_log = list(state.get("audit_log", []))

        errors.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "agent": "ReconciliationAgent",
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        )

        audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc),
                "agent": "ReconciliationAgent",
                "action": "Reconciliation failed",
                "input": {
                    "question_count": len(state.get("questions", [])),
                },
                "output": {
                    "reconciliation_status": "failed",
                    "error": str(exc),
                },
            }
        )

        return {
            **state,
            "reconciliation_status": "failed",
            "reconciliation_results": {},
            "question_results": state.get("question_results", {}),
            "errors": errors,
            "audit_log": audit_log,
            "final_route": "HUMAN_REVIEW",
        }