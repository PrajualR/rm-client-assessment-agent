# Client Assessment Agentic Workflow POC

A proof-of-concept for an agentic client assessment workflow built with Python and LangGraph.

## Overview

This POC demonstrates a four-agent workflow that processes a plain-text client assessment document, extracts questionnaire data, verifies the extracted values, and determines the appropriate confidence-based outcome.

## Agents

1. **Ingestion Agent** – validates that input document text is available.
2. **Extraction Agent** – extracts configured client fields from the document.
3. **Verification Agent** – applies mock verification rules and assigns confidence scores.
4. **Reconciliation Agent** – converts confidence into the final routing outcome.

LangGraph orchestrates the agents as a stateful workflow with conditional routing at the end.

## Confidence Routing

| Confidence | Route |
|---|---|
| `>= 0.85` | `AUTO_FILL` |
| `>= 0.60` and `< 0.85` | `ESCALATE` |
| `< 0.60` | `HUMAN_REVIEW` |

The final case route follows this priority:

```text
HUMAN_REVIEW > ESCALATE > AUTO_FILL