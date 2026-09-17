from datetime import datetime, timezone


def auto_fill_handler(state):
    audit_log = list(state.get("audit_log", []))

    audit_log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "WorkflowRouter",
            "action": "Assessment routed for automatic form population",
            "input": {
                "final_route": state["final_route"],
            },
            "output": {
                "workflow_status": "AUTO_FILL_READY",
                "next_action": "Populate assessment form automatically",
            },
        }
    )

    return {
        "workflow_status": "AUTO_FILL_READY",
        "audit_log": audit_log,
    }


def escalation_handler(state):
    audit_log = list(state.get("audit_log", []))

    escalation_questions = [
        question_id
        for question_id, result in state.get("reconciliation_results", {}).items()
        if result["route"] == "ESCALATE"
    ]

    audit_log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "WorkflowRouter",
            "action": "Assessment routed for escalation",
            "input": {
                "final_route": state["final_route"],
                "question_ids": escalation_questions,
            },
            "output": {
                "workflow_status": "ESCALATION_REQUIRED",
                "next_action": "Review escalated questionnaire answers",
            },
        }
    )

    return {
        "workflow_status": "ESCALATION_REQUIRED",
        "audit_log": audit_log,
    }


def human_review_handler(state):
    audit_log = list(state.get("audit_log", []))

    review_questions = [
        question_id
        for question_id, result in state.get("reconciliation_results", {}).items()
        if result["route"] == "HUMAN_REVIEW"
    ]

    audit_log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "WorkflowRouter",
            "action": "Assessment routed for mandatory human review",
            "input": {
                "final_route": state["final_route"],
                "question_ids": review_questions,
            },
            "output": {
                "workflow_status": "HUMAN_REVIEW_REQUIRED",
                "next_action": ("Obtain reviewer decision before proceeding"),
            },
        }
    )

    return {
        "workflow_status": "HUMAN_REVIEW_REQUIRED",
        "audit_log": audit_log,
    }
