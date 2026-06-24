import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getRiskDetail, submitRisk } from "../api/risks";
import type { RiskDetailResponse, RiskRecordRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RiskSubmitState =
  | { status: "loading" }
  | { status: "success"; detail: RiskDetailResponse }
  | { status: "error"; message: string };

export function RiskSubmitPage() {
  const { isAuthenticated, token } = useAuth();
  const { riskRecordId } = useParams();
  const navigate = useNavigate();
  const [riskDetail, setRiskDetail] = useState<RiskSubmitState>({
    status: "loading",
  });
  const [reason, setReason] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    if (!token || !riskRecordId) {
      return;
    }

    const tokenToUse = token;
    const idToLoad = riskRecordId;

    async function loadRiskDetail() {
      try {
        const detail = await getRiskDetail(tokenToUse, idToLoad);
        if (isCurrent) {
          setRiskDetail({ status: "success", detail });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setRiskDetail({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
      }
    }

    void loadRiskDetail();

    return () => {
      isCurrent = false;
    };
  }, [riskRecordId, token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !riskRecordId) {
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await submitRisk(token, riskRecordId, { reason: reason.trim() || null });
      navigate(`/risks/${riskRecordId}`, {
        replace: true,
        state: { successMessage: "Risk submitted successfully." },
      });
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Unable to submit risk.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (!riskRecordId) {
    return <Navigate replace to="/risks" />;
  }

  if (riskDetail.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading risk submission details...
      </p>
    );
  }

  if (riskDetail.status === "error") {
    return (
      <section className="risk-submit-page" aria-labelledby="submission-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="submission-load-error">Unable to load risk detail.</strong>
          <span>{riskDetail.message}</span>
        </div>
      </section>
    );
  }

  const risk = getRiskRecord(riskDetail.detail);

  if (!risk) {
    return (
      <section className="risk-submit-page" aria-labelledby="submission-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="submission-load-error">Unable to load risk detail.</strong>
          <span>The API response did not include a risk record.</span>
        </div>
      </section>
    );
  }

  const initialAssessmentExists = (riskDetail.detail.assessments ?? []).some(
    (assessment) => assessment.assessment_type === "INITIAL",
  );

  return (
    <section className="risk-submit-page" aria-labelledby="submit-risk-heading">
      <Link className="back-link" to={`/risks/${risk.id}`}>
        Back to risk detail
      </Link>
      <p className="eyebrow">Risk workflow</p>
      <h1 id="submit-risk-heading">Submit risk</h1>
      <p className="create-risk-description">
        Confirm the draft risk before it enters the workflow.
      </p>

      <section className="submission-summary" aria-labelledby="submission-summary-heading">
        <h2 id="submission-summary-heading">Submission summary</h2>
        <dl className="metadata-grid">
          <div>
            <dt>Risk ID</dt>
            <dd>{getRiskDisplayId(risk)}</dd>
          </div>
          <div>
            <dt>Domain</dt>
            <dd>{risk.domain}</dd>
          </div>
          <div>
            <dt>Workflow status</dt>
            <dd>{risk.workflow_status}</dd>
          </div>
          <div>
            <dt>Initial assessment</dt>
            <dd>{initialAssessmentExists ? "Recorded" : "Not recorded"}</dd>
          </div>
        </dl>
        <p className="detail-copy">{risk.problem_description}</p>
      </section>

      {!initialAssessmentExists && (
        <div className="workflow-warning" role="note">
          An initial assessment should be recorded before submission.
        </div>
      )}

      {risk.workflow_status !== "DRAFT" && (
        <div className="workflow-warning" role="note">
          This risk is no longer in DRAFT status. The backend may reject a
          duplicate submission.
        </div>
      )}

      <form className="submission-form" onSubmit={handleSubmit}>
        <label htmlFor="submission-reason">Submission reason <span>(optional)</span></label>
        <textarea
          disabled={isSubmitting}
          id="submission-reason"
          name="reason"
          onChange={(event) => setReason(event.target.value)}
          value={reason}
        />

        {errorMessage && (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        )}

        <div className="form-actions">
          <button disabled={isSubmitting} type="submit">
            {isSubmitting ? "Submitting risk..." : "Submit risk"}
          </button>
          <Link className="secondary-link" to={`/risks/${risk.id}`}>
            Back to risk detail
          </Link>
        </div>
      </form>
    </section>
  );
}

function getRiskRecord(detail: RiskDetailResponse): RiskRecordRead | null {
  return detail.risk || detail.risk_record || detail.record || null;
}

function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}
