import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { createRiskAction } from "../api/riskActions";
import { getRiskDetail } from "../api/risks";
import type { RiskDetailResponse, RiskRecordRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RiskSummaryState =
  | { status: "loading" }
  | { status: "success"; detail: RiskDetailResponse }
  | { status: "error"; message: string };

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function RiskActionCreatePage() {
  const { isAuthenticated, token } = useAuth();
  const { riskRecordId } = useParams();
  const navigate = useNavigate();
  const [riskSummary, setRiskSummary] = useState<RiskSummaryState>({
    status: "loading",
  });
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [actionOwnerUserId, setActionOwnerUserId] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    if (!token || !riskRecordId) {
      return;
    }

    const tokenToUse = token;
    const idToLoad = riskRecordId;

    async function loadRiskSummary() {
      try {
        const detail = await getRiskDetail(tokenToUse, idToLoad);
        if (isCurrent) {
          setRiskSummary({ status: "success", detail });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setRiskSummary({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
      }
    }

    void loadRiskSummary();

    return () => {
      isCurrent = false;
    };
  }, [riskRecordId, token]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !riskRecordId) {
      return;
    }

    const ownerUserId = actionOwnerUserId.trim();

    if (ownerUserId && !UUID_PATTERN.test(ownerUserId)) {
      setErrorMessage(
        "Action owner must be a valid user UUID, or leave it blank.",
      );
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await createRiskAction(token, {
        risk_record_id: riskRecordId,
        title: title.trim(),
        description: description.trim() || null,
        due_date: dueDate || null,
        action_owner_user_id: ownerUserId || null,
      });
      navigate(`/risks/${riskRecordId}`, {
        replace: true,
        state: { successMessage: "Mitigation action created successfully." },
      });
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to create mitigation action.",
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

  if (riskSummary.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading risk summary...
      </p>
    );
  }

  if (riskSummary.status === "error") {
    return (
      <section className="risk-action-page" aria-labelledby="action-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="action-load-error">Unable to load risk detail.</strong>
          <span>{riskSummary.message}</span>
        </div>
      </section>
    );
  }

  const risk = getRiskRecord(riskSummary.detail);

  if (!risk) {
    return (
      <section className="risk-action-page" aria-labelledby="action-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="action-load-error">Unable to load risk detail.</strong>
          <span>The API response did not include a risk record.</span>
        </div>
      </section>
    );
  }

  return (
    <section className="risk-action-page" aria-labelledby="action-heading">
      <Link className="back-link" to={`/risks/${risk.id}`}>
        Back to risk detail
      </Link>
      <p className="eyebrow">Mitigation action</p>
      <h1 id="action-heading">Create mitigation action</h1>
      <p className="create-risk-description">
        Record a follow-up action for {getRiskDisplayId(risk)} in {risk.domain}.
      </p>

      <form className="action-form" onSubmit={handleSubmit}>
        <label htmlFor="action-title">Title</label>
        <input
          disabled={isSubmitting}
          id="action-title"
          name="title"
          onChange={(event) => setTitle(event.target.value)}
          required
          type="text"
          value={title}
        />

        <label htmlFor="action-description">Description <span>(optional)</span></label>
        <textarea
          disabled={isSubmitting}
          id="action-description"
          name="description"
          onChange={(event) => setDescription(event.target.value)}
          value={description}
        />

        <label htmlFor="action-due-date">Due date <span>(optional)</span></label>
        <input
          disabled={isSubmitting}
          id="action-due-date"
          name="due_date"
          onChange={(event) => setDueDate(event.target.value)}
          type="date"
          value={dueDate}
        />

        <label htmlFor="action-owner-user-id">
          Action owner user UUID <span>(optional)</span>
        </label>
        <input
          aria-describedby="action-owner-user-id-help"
          autoComplete="off"
          disabled={isSubmitting}
          id="action-owner-user-id"
          name="action_owner_user_id"
          onChange={(event) => setActionOwnerUserId(event.target.value)}
          placeholder="Leave blank or enter a user UUID"
          type="text"
          value={actionOwnerUserId}
        />
        <p className="field-help" id="action-owner-user-id-help">
          Leave blank if no owner is assigned yet. Names or roles are not
          accepted here.
        </p>

        {errorMessage && (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        )}

        <div className="form-actions">
          <button disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating action..." : "Create mitigation action"}
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
