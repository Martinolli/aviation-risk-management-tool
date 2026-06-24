import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { listCommittees } from "../api/committees";
import { createRiskDecision } from "../api/riskDecisions";
import { getRiskDetail } from "../api/risks";
import type {
  CommitteeRead,
  RiskDecisionType,
  RiskAssessmentRead,
  RiskDetailResponse,
  RiskRecordRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

const DECISION_OPTIONS: { value: RiskDecisionType; label: string }[] = [
  { value: "APPROVE", label: "Approve" },
  { value: "REJECT", label: "Reject" },
  { value: "ESCALATE", label: "Escalate" },
  { value: "RETURN_FOR_REVISION", label: "Return for revision" },
  { value: "ACCEPT_RESIDUAL_RISK", label: "Accept residual risk" },
  { value: "CLOSE", label: "Close" },
];

type DecisionPageState =
  | { status: "loading" }
  | {
      status: "success";
      detail: RiskDetailResponse;
      committees: CommitteeRead[];
    }
  | { status: "error"; message: string };

export function RiskDecisionCreatePage() {
  const { isAuthenticated, token } = useAuth();
  const { riskRecordId } = useParams();
  const navigate = useNavigate();
  const [pageState, setPageState] = useState<DecisionPageState>({
    status: "loading",
  });
  const [committeeId, setCommitteeId] = useState("");
  const [decisionType, setDecisionType] = useState<RiskDecisionType | "">("");
  const [decisionText, setDecisionText] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    if (!token || !riskRecordId) {
      return;
    }

    const tokenToUse = token;
    const idToLoad = riskRecordId;

    async function loadDecisionContext() {
      try {
        const [detail, committees] = await Promise.all([
          getRiskDetail(tokenToUse, idToLoad),
          listCommittees(tokenToUse),
        ]);
        if (isCurrent) {
          setPageState({ status: "success", detail, committees });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setPageState({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
      }
    }

    void loadDecisionContext();

    return () => {
      isCurrent = false;
    };
  }, [riskRecordId, token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !riskRecordId || !decisionType) {
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await createRiskDecision(token, {
        risk_record_id: riskRecordId,
        committee_id: committeeId,
        decision_type: decisionType,
        decision_text: decisionText.trim(),
      });
      navigate(`/risks/${riskRecordId}`, {
        replace: true,
        state: { successMessage: "Committee decision recorded successfully." },
      });
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to record committee decision.",
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

  if (pageState.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading decision context...
      </p>
    );
  }

  if (pageState.status === "error") {
    return (
      <section className="risk-decision-page" aria-labelledby="decision-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="decision-load-error">Unable to load decision context.</strong>
          <span>{pageState.message}</span>
        </div>
      </section>
    );
  }

  const risk = getRiskRecord(pageState.detail);

  if (!risk) {
    return (
      <section className="risk-decision-page" aria-labelledby="decision-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="decision-load-error">Unable to load risk detail.</strong>
          <span>The API response did not include a risk record.</span>
        </div>
      </section>
    );
  }

  const initialAssessment = pageState.detail.assessments?.find(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const residualAssessment = pageState.detail.assessments?.find(
    (assessment) => assessment.assessment_type === "RESIDUAL",
  );

  return (
    <section className="risk-decision-page" aria-labelledby="decision-heading">
      <Link className="back-link" to={`/risks/${risk.id}`}>
        Back to risk detail
      </Link>
      <p className="eyebrow">Committee decision</p>
      <h1 id="decision-heading">Record committee decision</h1>

      <section className="decision-summary" aria-labelledby="decision-summary-heading">
        <h2 id="decision-summary-heading">Risk summary</h2>
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
            <dt>Lifecycle status</dt>
            <dd>{risk.lifecycle_status}</dd>
          </div>
        </dl>
        <p className="detail-copy">{risk.problem_description}</p>
        <div className="decision-assessment-summary">
          <p>Initial assessment: {getAssessmentSummary(initialAssessment)}</p>
          <p>Residual assessment: {getAssessmentSummary(residualAssessment)}</p>
        </div>
      </section>

      <form className="decision-form" onSubmit={handleSubmit}>
        <label htmlFor="committee-id">Committee</label>
        <select
          disabled={isSubmitting || pageState.committees.length === 0}
          id="committee-id"
          name="committee_id"
          onChange={(event) => setCommitteeId(event.target.value)}
          required
          value={committeeId}
        >
          <option value="">Select committee</option>
          {pageState.committees.map((committee) => (
            <option key={committee.id} value={committee.id}>
              {committee.name} ({committee.authority_level})
            </option>
          ))}
        </select>

        <label htmlFor="decision-type">Decision type</label>
        <select
          disabled={isSubmitting}
          id="decision-type"
          name="decision_type"
          onChange={(event) => setDecisionType(event.target.value as RiskDecisionType)}
          required
          value={decisionType}
        >
          <option value="">Select decision type</option>
          {DECISION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        {decisionType === "ACCEPT_RESIDUAL_RISK" && !residualAssessment && (
          <p className="decision-guidance">
            Residual risk acceptance normally requires a residual assessment.
          </p>
        )}
        {decisionType === "CLOSE" && (
          <p className="decision-guidance">
            Closure should only be selected when required actions and acceptance
            evidence are complete.
          </p>
        )}
        {decisionType === "ESCALATE" && (
          <p className="decision-note">
            Escalation should identify the next authority level in the decision
            text.
          </p>
        )}

        <label htmlFor="decision-text">Decision text</label>
        <textarea
          disabled={isSubmitting}
          id="decision-text"
          name="decision_text"
          onChange={(event) => setDecisionText(event.target.value)}
          required
          value={decisionText}
        />

        {pageState.committees.length === 0 && (
          <p className="decision-guidance">No active committees are available.</p>
        )}

        {errorMessage && (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        )}

        <div className="form-actions">
          <button
            disabled={isSubmitting || pageState.committees.length === 0}
            type="submit"
          >
            {isSubmitting ? "Recording decision..." : "Record committee decision"}
          </button>
          <Link className="secondary-link" to={`/risks/${risk.id}`}>
            Cancel
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

function getAssessmentSummary(assessment: RiskAssessmentRead | undefined): string {
  if (!assessment) {
    return "Not recorded";
  }

  return `${assessment.risk_level || "Risk level not specified"} (${assessment.calculated_score ?? "no score"})`;
}
