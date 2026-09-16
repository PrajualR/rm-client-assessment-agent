from datetime import datetime, timezone


def ingestion_agent(state):
    document_text = state.get("document_text", "")
    audit_log = list(state.get("audit_log", []))
    errors = list(state.get("errors", []))

    try:
        if not isinstance(document_text, str):
            raise TypeError("Document content must be a string.")

        if not document_text.strip():
            raise ValueError("Document content is empty.")

        audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "IngestionAgent",
                "action": "Validated input document",
                "input": {
                    "document_length": len(document_text),
                },
                "output": {
                    "ingestion_status": "success",
                },
            }
        )

        return {
            "ingestion_status": "success",
            "workflow_status": "ingestion_completed",
            "errors": errors,
            "audit_log": audit_log,
        }

    except Exception as exc:
        error_message = str(exc)

        errors.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "IngestionAgent",
                "error_type": type(exc).__name__,
                "message": error_message,
            }
        )

        audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "IngestionAgent",
                "action": "Input document validation failed",
                "input": {
                    "document_type": type(document_text).__name__,
                },
                "output": {
                    "ingestion_status": "failed",
                    "error": error_message,
                },
            }
        )

        return {
            "ingestion_status": "failed",
            "workflow_status": "failed",
            "final_route": "HUMAN_REVIEW",
            "errors": errors,
            "audit_log": audit_log,
        }