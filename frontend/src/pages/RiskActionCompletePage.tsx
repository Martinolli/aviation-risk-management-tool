import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { completeRiskAction } from "../api/riskActions";
import { getRiskDetail } from "../api/risks";
import type {
  RiskActionRead,
  RiskDetailResponse,
  RiskRecordRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RiskActionDetailState =
  | { status: "loading" }
  | { status: "success"; detail: RiskDetailResponse }
  | { status: "error"; message: string };

export function RiskActionCompletePage() {
  const { isAuthenticated, token } = useAuth();
  const { riskRecordId, riskActionId } = useParams();
  const navigate = useNavigate();
  const [riskDetail, setRiskDetail] = useState<RiskActionDetailState>({
    status: "loading",
  });
  const [completionNotes, setCompletionNotes] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    if (!token || !riskRecordId || !riskActionId) {
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
  }, [riskActionId, riskRecordId, token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !riskRecordId || !riskActionId) {
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await completeRiskAction(token, riskActionId, {
        completion_notes: completionNotes.trim() || null,
      });
      navigate(`/risks/${riskRecordId}`, {
        replace: true,
        state: { successMessage: "Mitigation action completed successfully." },
      });
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to complete mitigation action.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (!riskRecordId || !riskActionId) {
    return <Navigate replace to="/risks" />;
  }

  if (riskDetail.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading mitigation action...
      </p>
    );
  }

  if (riskDetail.status === "error") {
    return (
      <section className="action-complete-page" aria-labelledby="completion-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="completion-load-error">Unable to load risk detail.</strong>
          <span>{riskDetail.message}</span>
        </div>
      </section>
    );
  }

  const risk = getRiskRecord(riskDetail.detail);
  const action = riskDetail.detail.actions?.find(
    (candidate) => candidate.id === riskActionId,
  );

  if (!risk || !action) {
    return (
      <section className="action-complete-page" aria-labelledby="action-not-found">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="action-not-found">Mitigation action not found for this risk.</strong>
        </div>
      </section>
    );
  }

  const isCompleted = isActionCompleted(action);

  return (
    <section className="action-complete-page" aria-labelledby="complete-action-heading">
      <Link className="back-link" to={`/risks/${risk.id}`}>
        Back to risk detail
      </Link>
      <p className="eyebrow">Mitigation action</p>
      <h1 id="complete-action-heading">Complete mitigation action</h1>

      <section className="completion-summary" aria-labelledby="completion-summary-heading">
        <h2 id="completion-summary-heading">Action summary</h2>
        <dl className="metadata-grid">
          <div>
            <dt>Risk ID</dt>
            <dd>{getRiskDisplayId(risk)}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>{action.status || "Not specified"}</dd>
          </div>
          {action.due_date && (
            <div>
              <dt>Due date</dt>
              <dd>{action.due_date}</dd>
            </div>
          )}
        </dl>
        <h3>{action.title || "Untitled action"}</h3>
        {action.description && <p className="detail-copy">{action.description}</p>}
      </section>

      {isCompleted ? (
        <section className="completion-summary" aria-labelledby="already-completed-heading">
          <h2 id="already-completed-heading">This mitigation action is already completed.</h2>
          {action.completed_at && (
            <p className="muted-text">Completed {formatDateTime(action.completed_at)}</p>
          )}
          {action.completion_notes && (
            <p className="detail-copy">{action.completion_notes}</p>
          )}
        </section>
      ) : (
        <form className="completion-form" onSubmit={handleSubmit}>
          <label htmlFor="completion-notes">Completion notes <span>(optional)</span></label>
          <textarea
            disabled={isSubmitting}
            id="completion-notes"
            name="completion_notes"
            onChange={(event) => setCompletionNotes(event.target.value)}
            value={completionNotes}
          />

          {errorMessage && (
            <p className="form-error" role="alert">
              {errorMessage}
            </p>
          )}

          <div className="form-actions">
            <button disabled={isSubmitting} type="submit">
              {isSubmitting ? "Completing action..." : "Complete mitigation action"}
            </button>
            <Link className="secondary-link" to={`/risks/${risk.id}`}>
              Back to risk detail
            </Link>
          </div>
        </form>
      )}
    </section>
  );
}

function getRiskRecord(detail: RiskDetailResponse): RiskRecordRead | null {
  return detail.risk || detail.risk_record || detail.record || null;
}

function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

function isActionCompleted(action: RiskActionRead): boolean {
  return (
    action.status === "COMPLETED" ||
    (action.completed_at !== null && action.completed_at !== undefined)
  );
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not available" : date.toLocaleString();
}
