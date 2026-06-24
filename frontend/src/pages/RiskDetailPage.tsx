import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getRiskDetail } from "../api/risks";
import type { RiskDetailResponse, RiskRecordRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RiskDetailState =
  | { status: "loading" }
  | { status: "success"; detail: RiskDetailResponse }
  | { status: "error"; message: string };

export function RiskDetailPage() {
  const { isAuthenticated, token } = useAuth();
  const { riskRecordId } = useParams();
  const location = useLocation();
  const [riskDetail, setRiskDetail] = useState<RiskDetailState>({
    status: "loading",
  });

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

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (!riskRecordId) {
    return <Navigate replace to="/risks" />;
  }

  if (riskDetail.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading risk detail...
      </p>
    );
  }

  if (riskDetail.status === "error") {
    return (
      <section className="risk-detail-page" aria-labelledby="risk-detail-error">
        <Link className="back-link" to="/risks">
          Back to risk records
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="risk-detail-error">Unable to load risk detail.</strong>
          <span>{riskDetail.message}</span>
        </div>
      </section>
    );
  }

  const risk = getRiskRecord(riskDetail.detail);

  if (!risk) {
    return (
      <section className="risk-detail-page" aria-labelledby="risk-detail-error">
        <Link className="back-link" to="/risks">
          Back to risk records
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="risk-detail-error">Unable to load risk detail.</strong>
          <span>The API response did not include a risk record.</span>
        </div>
      </section>
    );
  }

  const assessments = riskDetail.detail.assessments ?? [];
  const actions = riskDetail.detail.actions ?? [];
  const decisions = riskDetail.detail.decisions ?? [];
  const initialAssessmentExists = assessments.some(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const initialAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const successMessage = getSuccessMessage(location.state);

  return (
    <section className="risk-detail-page" aria-labelledby="risk-detail-heading">
      <Link className="back-link" to="/risks">
        Back to risk records
      </Link>

      {successMessage && (
        <p aria-live="polite" className="workspace-success" role="status">
          {successMessage}
        </p>
      )}

      <header className="risk-detail-header">
        <p className="eyebrow">Risk record</p>
        <h1 id="risk-detail-heading">{getRiskDisplayId(risk)}</h1>
        <div className="risk-detail-tags">
          <span className="status-badge">{risk.domain}</span>
          <span className="status-badge">{risk.workflow_status}</span>
          <span className="status-badge">{risk.lifecycle_status}</span>
        </div>
        <p className="muted-text">
          Created {formatDateTime(risk.created_at)} · Updated {formatDateTime(risk.updated_at)}
        </p>
        <section className="workflow-action-card" aria-labelledby="workflow-action-heading">
          <strong id="workflow-action-heading">Workflow action</strong>
          {risk.workflow_status === "DRAFT" ? (
            <Link className="button" to={`/risks/${risk.id}/submit`}>
              Submit risk
            </Link>
          ) : (
            <span className="detail-action-muted">Risk has already been submitted.</span>
          )}
          <span
            className={
              initialAssessmentExists ? "workflow-confirmed" : "workflow-warning-text"
            }
          >
            {initialAssessmentExists
              ? "Initial assessment recorded."
              : "Initial assessment not recorded yet."}
          </span>
        </section>
      </header>

      <DetailSection title="Problem description">
        <p className="detail-copy">{risk.problem_description}</p>
      </DetailSection>

      <DetailSection title="Source trigger">
        <p className="detail-copy">{risk.source_trigger || "Not specified."}</p>
      </DetailSection>

      <DetailSection title="Ownership and metadata">
        <dl className="metadata-grid">
          <div>
            <dt>Owner</dt>
            <dd>{risk.owner_user_id || "Not assigned."}</dd>
          </div>
          <div>
            <dt>Created by</dt>
            <dd>{risk.created_by_user_id || "Not specified."}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDateTime(risk.created_at)}</dd>
          </div>
          <div>
            <dt>Last updated</dt>
            <dd>{formatDateTime(risk.updated_at)}</dd>
          </div>
        </dl>
      </DetailSection>

      <DetailSection title="Assessments">
        <div className="detail-section-action">
          {initialAssessmentExists ? (
            <span className="detail-action-muted">
              Initial assessment already recorded.
            </span>
          ) : (
            <Link className="button" to={`/risks/${risk.id}/assessments/new`}>
              Add initial assessment
            </Link>
          )}
        </div>
        {assessments.length === 0 ? (
          <p className="detail-empty">No assessments recorded yet.</p>
        ) : (
          <ul className="detail-list">
            {assessments.map((assessment) => (
              <li key={assessment.id}>
                <strong>{assessment.assessment_type || "Assessment"}</strong>
                <span>
                  Severity: {assessment.severity || "Not specified"} · Likelihood: {assessment.likelihood || "Not specified"} · Risk level: {assessment.risk_level || "Not specified"}
                </span>
                {assessment.calculated_score !== null &&
                  assessment.calculated_score !== undefined && (
                    <span>Calculated score: {assessment.calculated_score}</span>
                  )}
                <div className="assessment-flags">
                  <span>Tolerable: {formatOptionalBoolean(assessment.is_tolerable)}</span>
                  <span>Mitigation: {formatOptionalBoolean(assessment.requires_mitigation)}</span>
                  <span>Escalation: {formatOptionalBoolean(assessment.requires_escalation)}</span>
                </div>
                {assessment.rationale && <span>Rationale: {assessment.rationale}</span>}
                <span>
                  Recorded {formatDateTime(assessment.assessed_at || assessment.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </DetailSection>

      <DetailSection title="Mitigation actions">
        <div className="detail-section-action">
          <Link className="button" to={`/risks/${risk.id}/actions/new`}>
            Add mitigation action
          </Link>
        </div>
        {initialAssessment?.requires_mitigation === true && (
          <p className="guidance-note">
            This risk assessment requires mitigation.
          </p>
        )}
        {initialAssessment?.requires_mitigation === false && (
          <p className="guidance-note">
            Mitigation is not required by the current assessment, but actions
            may still be recorded if needed.
          </p>
        )}
        {actions.length === 0 ? (
          <p className="detail-empty">No mitigation actions recorded yet.</p>
        ) : (
          <ul className="detail-list">
            {actions.map((action) => (
              <li key={action.id}>
                <strong>{action.title || "Untitled action"}</strong>
                <span>{action.status || "Status not specified"}</span>
                {action.description && <span>{action.description}</span>}
                <div className="action-metadata">
                  {action.action_owner_user_id && (
                    <span>Owner: {action.action_owner_user_id}</span>
                  )}
                  {action.due_date && <span>Due: {action.due_date}</span>}
                  {action.completed_at && (
                    <span>Completed: {formatDateTime(action.completed_at)}</span>
                  )}
                </div>
                {action.completion_notes && (
                  <span>Completion notes: {action.completion_notes}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </DetailSection>

      <DetailSection title="Committee decisions">
        {decisions.length === 0 ? (
          <p className="detail-empty">No committee decisions recorded yet.</p>
        ) : (
          <ul className="detail-list">
            {decisions.map((decision) => (
              <li key={decision.id}>
                <strong>{decision.decision_type || "Decision"}</strong>
                <span>{decision.decision_text || "No decision text provided."}</span>
              </li>
            ))}
          </ul>
        )}
      </DetailSection>
    </section>
  );
}

function DetailSection({
  children,
  title,
}: {
  children: React.ReactNode;
  title: string;
}) {
  return (
    <section className="detail-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function getRiskRecord(detail: RiskDetailResponse): RiskRecordRead | null {
  return detail.risk || detail.risk_record || detail.record || null;
}

function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not available" : date.toLocaleString();
}

function formatOptionalBoolean(value: boolean | null | undefined): string {
  if (value === null || value === undefined) {
    return "Not specified";
  }

  return value ? "Yes" : "No";
}

function getSuccessMessage(state: unknown): string | null {
  if (
    !state ||
    typeof state !== "object" ||
    !("successMessage" in state) ||
    typeof state.successMessage !== "string"
  ) {
    return null;
  }

  return state.successMessage;
}
