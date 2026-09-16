from datetime import datetime

from src.config.settings import settings
from src.models.assessment_models import VerificationResult


def verify_field(field_name: str, value):
    """
    Verify one extracted field using deterministic business rules.
    """

    if value is None or str(value).strip() == "":
        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="REVIEW_REQUIRED",
            confidence=0.0,
            reason="Value is missing and requires human review.",
        )

    normalized_value = str(value).strip()

    if field_name == "country_of_incorporation":
        if normalized_value in settings.allowed_countries:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="PASSED",
                confidence=0.95,
                reason="Country is present in the configured allowed-country list.",
            )

        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="FAILED",
            confidence=0.30,
            reason="Country is not present in the configured allowed-country list.",
        )

    if field_name == "business_activity":
        if len(normalized_value) >= 3:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="PASSED",
                confidence=0.95,
                reason="Business activity contains a valid descriptive value.",
            )

        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="FAILED",
            confidence=0.30,
            reason="Business activity value is too short.",
        )

    if field_name == "annual_revenue":
        try:
            revenue = float(normalized_value)

            if revenue >= 0:
                return VerificationResult(
                    field_name=field_name,
                    value=value,
                    verification_status="PASSED",
                    confidence=0.95,
                    reason="Annual revenue is a valid non-negative numeric value.",
                )

            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="FAILED",
                confidence=0.30,
                reason="Annual revenue cannot be negative.",
            )

        except ValueError:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="FAILED",
                confidence=0.30,
                reason="Annual revenue must be numeric.",
            )

    if field_name == "existing_bank_relationship":
        if normalized_value in settings.allowed_bank_relationship_values:
            return VerificationResult(
                field_name=field_name,
                value=value,
                verification_status="PASSED",
                confidence=0.95,
                reason="Bank relationship value is valid.",
            )

        return VerificationResult(
            field_name=field_name,
            value=value,
            verification_status="FAILED",
            confidence=0.30,
            reason="Bank relationship must be Yes or No.",
        )

    return VerificationResult(
        field_name=field_name,
        value=value,
        verification_status="REVIEW_REQUIRED",
        confidence=0.50,
        reason="No verification rule is configured for this field.",
    )


def verification_agent(state):
    """
    Verify all extracted questionnaire answers.
    """

    try:
        verification_results = {}
        question_results = dict(state.get("question_results", {}))

        for question in state["questions"]:
            # QuestionnaireQuestion is a Pydantic model.
            question_id = question.question_id
            field_name = question.field_name

            extracted_result = question_results.get(question_id, {})

            extracted_value = extracted_result.get("extracted_value")

            verification_result = verify_field(
                field_name=field_name,
                value=extracted_value,
            )

            verification_results[field_name] = (
                verification_result.model_dump()
            )

            question_results[question_id] = {
                **extracted_result,
                "verification_status": verification_result.verification_status,
                "verification_confidence": verification_result.confidence,
                "verification_reason": verification_result.reason,
            }

        audit_log = list(state.get("audit_log", []))

        audit_log.append(
            {
                "timestamp": datetime.now(),
                "agent": "VerificationAgent",
                "action": "Verified questionnaire answers",
                "input": {
                    "question_count": len(state["questions"]),
                },
                "output": {
                    "verification_status": "success",
                    "verified_field_count": len(verification_results),
                },
            }
        )

        return {
            **state,
            "verification_status": "success",
            "verification_results": verification_results,
            "question_results": question_results,
            "audit_log": audit_log,
        }

    except Exception as exc:
        errors = list(state.get("errors", []))
        audit_log = list(state.get("audit_log", []))

        error_details = {
            "timestamp": datetime.now(),
            "agent": "VerificationAgent",
            "error_type": type(exc).__name__,
            "message": str(exc),
        }

        errors.append(error_details)

        audit_log.append(
            {
                "timestamp": datetime.now(),
                "agent": "VerificationAgent",
                "action": "Verification failed",
                "input": {
                    "question_count": len(state.get("questions", [])),
                },
                "output": {
                    "verification_status": "failed",
                    "error": str(exc),
                },
            }
        )

        return {
            **state,
            "verification_status": "failed",
            "verification_results": {},
            "question_results": state.get("question_results", {}),
            "errors": errors,
            "audit_log": audit_log,
            "final_route": "HUMAN_REVIEW",
        }