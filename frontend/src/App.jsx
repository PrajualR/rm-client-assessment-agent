import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const sampleDocument = `Country of Incorporation: India
Business Activity: Information Technology Services
Annual Revenue: INR 48.5 Crores
Existing Bank Relationship: Yes`;

function getRouteClass(route) {
  return route.toLowerCase().replace("_", "-");
}

function formatConfidence(confidence) {
  if (confidence === null || confidence === undefined) {
    return "N/A";
  }

  return `${Math.round(confidence * 100)}%`;
}

function App() {
  const [caseId, setCaseId] = useState("CASE-001");
  const [documentText, setDocumentText] = useState(sampleDocument);
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [approved, setApproved] = useState(false);

  async function submitAssessment(event) {
    event.preventDefault();

    setLoading(true);
    setError("");
    setAssessment(null);
    setApproved(false);

    try {
      const response = await fetch(`${API_URL}/assessments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          case_id: caseId,
          document_text: documentText,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Assessment processing failed.");
      }

      setAssessment(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  function approveAssessment() {
    setApproved(true);
  }

  return (
    <main className="page">
      <section className="container">
        <header className="header">
          <div>
            <p className="eyebrow">Agentic Workflow Demo</p>
            <h1>Client Assessment</h1>
            <p className="subtitle">
              Extract, verify, and reconcile client questionnaire responses.
            </p>
          </div>

          <div className="status-pill">
            <span className="status-dot" />
            Demo
          </div>
        </header>

        <section className="card">
          <div className="section-heading">
            <div>
              <h2>Document Input</h2>
              <p>Paste the client document and submit the assessment.</p>
            </div>
          </div>

          <form onSubmit={submitAssessment}>
            <label htmlFor="caseId">Case ID</label>
            <input
              id="caseId"
              value={caseId}
              onChange={(event) => setCaseId(event.target.value)}
              placeholder="CASE-001"
              required
            />

            <label htmlFor="documentText">Document Text</label>
            <textarea
              id="documentText"
              value={documentText}
              onChange={(event) => setDocumentText(event.target.value)}
              placeholder="Paste client document text here..."
              rows={9}
              required
            />

            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Processing..." : "Submit Assessment"}
            </button>
          </form>

          {error && <div className="error-box">{error}</div>}
        </section>

        {assessment && (
          <section className="card">
            <div className="result-header">
              <div>
                <p className="eyebrow">Assessment Result</p>
                <h2>{assessment.case_id}</h2>
              </div>

              <span
                className={`route-badge ${getRouteClass(
                  assessment.final_route
                )}`}
              >
                {assessment.final_route}
              </span>
            </div>

            <div className="summary-grid">
              <div className="summary-item">
                <span>Total Questions</span>
                <strong>{assessment.summary.total_questions}</strong>
              </div>

              <div className="summary-item">
                <span>Answered</span>
                <strong>{assessment.summary.answered_count}</strong>
              </div>

              <div className="summary-item">
                <span>Auto-fill</span>
                <strong>{assessment.summary.auto_fill_count}</strong>
              </div>

              <div className="summary-item">
                <span>Human Review</span>
                <strong>{assessment.summary.human_review_count}</strong>
              </div>
            </div>

            <div className="question-list">
              {assessment.question_results.map((question) => (
                <article
                  className={`question-card ${getRouteClass(
                    question.final_route
                  )}`}
                  key={question.question_id}
                >
                  <div className="question-topline">
                    <span className="question-number">
                      {question.question_id}
                    </span>

                    <span
                      className={`route-badge ${getRouteClass(
                        question.final_route
                      )}`}
                    >
                      {question.final_route}
                    </span>
                  </div>

                  <h3>{question.question}</h3>

                  <div className="field-value">
                    {question.final_value || "No value available"}
                  </div>

                  <div className="question-meta">
                    <span>
                      Confidence:{" "}
                      <strong>
                        {formatConfidence(question.final_confidence)}
                      </strong>
                    </span>

                    <span>
                      Verification:{" "}
                      <strong>
                        {question.verification_status || "N/A"}
                      </strong>
                    </span>
                  </div>

                  {question.final_reason && (
                    <p className="reason">{question.final_reason}</p>
                  )}
                </article>
              ))}
            </div>

            <div className="approval-area">
              {approved ? (
                <div className="approved-message">
                  Assessment approved for demo purposes.
                </div>
              ) : (
                <button
                  className="approve-button"
                  type="button"
                  onClick={approveAssessment}
                >
                  Approve Assessment
                </button>
              )}
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

export default App;