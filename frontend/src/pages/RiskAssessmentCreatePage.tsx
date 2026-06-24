import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  listLikelihoodLevels,
  listRiskLevels,
  listRiskMatrixCells,
  listSeverityLevels,
} from "../api/riskMatrix";
import { createRiskAssessment } from "../api/riskAssessments";
import type {
  RiskLevelRead,
  RiskLikelihoodLevelRead,
  RiskMatrixCellRead,
  RiskSeverityLevelRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RiskMatrixState =
  | { status: "loading" }
  | {
      status: "success";
      severityLevels: RiskSeverityLevelRead[];
      likelihoodLevels: RiskLikelihoodLevelRead[];
      riskLevels: RiskLevelRead[];
      cells: RiskMatrixCellRead[];
    }
  | { status: "error"; message: string };

export function RiskAssessmentCreatePage() {
  const { isAuthenticated, token } = useAuth();
  const { riskRecordId } = useParams();
  const navigate = useNavigate();
  const [matrix, setMatrix] = useState<RiskMatrixState>({ status: "loading" });
  const [severityLevelId, setSeverityLevelId] = useState("");
  const [likelihoodLevelId, setLikelihoodLevelId] = useState("");
  const [rationale, setRationale] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    if (!token || !riskRecordId) {
      return;
    }

    const tokenToUse = token;

    async function loadMatrix() {
      try {
        const [severityLevels, likelihoodLevels, riskLevels, cells] =
          await Promise.all([
            listSeverityLevels(tokenToUse),
            listLikelihoodLevels(tokenToUse),
            listRiskLevels(tokenToUse),
            listRiskMatrixCells(tokenToUse),
          ]);

        if (isCurrent) {
          setMatrix({
            status: "success",
            severityLevels,
            likelihoodLevels,
            riskLevels,
            cells,
          });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setMatrix({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
      }
    }

    void loadMatrix();

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
      await createRiskAssessment(token, {
        risk_record_id: riskRecordId,
        assessment_type: "INITIAL",
        severity_level_id: severityLevelId,
        likelihood_level_id: likelihoodLevelId,
        rationale: rationale.trim() || null,
      });
      navigate(`/risks/${riskRecordId}`, {
        replace: true,
        state: { successMessage: "Initial assessment created successfully." },
      });
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to create initial assessment.",
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

  if (matrix.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading risk matrix options...
      </p>
    );
  }

  if (matrix.status === "error") {
    return (
      <section className="risk-assessment-page" aria-labelledby="matrix-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="matrix-load-error">Unable to load risk matrix options.</strong>
          <span>{matrix.message}</span>
        </div>
      </section>
    );
  }

  const preview = getMatrixPreview(
    matrix.cells,
    matrix.riskLevels,
    severityLevelId,
    likelihoodLevelId,
  );

  return (
    <section className="risk-assessment-page" aria-labelledby="assessment-heading">
      <Link className="back-link" to={`/risks/${riskRecordId}`}>
        Back to risk detail
      </Link>
      <p className="eyebrow">Initial assessment</p>
      <h1 id="assessment-heading">Assess draft risk</h1>
      <p className="create-risk-description">
        Choose the configured severity and likelihood levels. The backend
        calculates the authoritative result when the assessment is created.
      </p>

      <form className="assessment-form" onSubmit={handleSubmit}>
        <label htmlFor="severity-level">Severity level</label>
        <select
          disabled={isSubmitting}
          id="severity-level"
          name="severity_level_id"
          onChange={(event) => setSeverityLevelId(event.target.value)}
          required
          value={severityLevelId}
        >
          <option value="">Select severity</option>
          {matrix.severityLevels.map((level) => (
            <option key={level.id} value={level.id}>
              {level.numeric_value} — {level.code}: {level.name}
            </option>
          ))}
        </select>

        <label htmlFor="likelihood-level">Likelihood level</label>
        <select
          disabled={isSubmitting}
          id="likelihood-level"
          name="likelihood_level_id"
          onChange={(event) => setLikelihoodLevelId(event.target.value)}
          required
          value={likelihoodLevelId}
        >
          <option value="">Select likelihood</option>
          {matrix.likelihoodLevels.map((level) => (
            <option key={level.id} value={level.id}>
              {level.numeric_value} — {level.code}: {level.name}
            </option>
          ))}
        </select>

        {preview && <MatrixPreview preview={preview} />}

        <label htmlFor="assessment-rationale">Rationale <span>(optional)</span></label>
        <textarea
          disabled={isSubmitting}
          id="assessment-rationale"
          name="rationale"
          onChange={(event) => setRationale(event.target.value)}
          value={rationale}
        />

        {errorMessage && (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        )}

        <div className="form-actions">
          <button disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating assessment..." : "Create initial assessment"}
          </button>
          <Link className="secondary-link" to={`/risks/${riskRecordId}`}>
            Cancel
          </Link>
        </div>
      </form>
    </section>
  );
}

function MatrixPreview({
  preview,
}: {
  preview: { cell: RiskMatrixCellRead; riskLevel: RiskLevelRead };
}) {
  const { cell, riskLevel } = preview;

  return (
    <aside className="matrix-preview" aria-live="polite">
      <strong>Matrix preview</strong>
      <p>The backend remains authoritative when this assessment is created.</p>
      <dl>
        <div>
          <dt>Score</dt>
          <dd>{cell.score ?? "Not specified"}</dd>
        </div>
        <div>
          <dt>Risk level</dt>
          <dd>{riskLevel.code}: {riskLevel.name}</dd>
        </div>
        <div>
          <dt>Tolerable</dt>
          <dd>{formatBoolean(riskLevel.is_tolerable)}</dd>
        </div>
        <div>
          <dt>Requires mitigation</dt>
          <dd>{formatBoolean(riskLevel.requires_mitigation)}</dd>
        </div>
        <div>
          <dt>Requires escalation</dt>
          <dd>{formatBoolean(riskLevel.requires_escalation)}</dd>
        </div>
      </dl>
    </aside>
  );
}

function getMatrixPreview(
  cells: RiskMatrixCellRead[],
  riskLevels: RiskLevelRead[],
  severityLevelId: string,
  likelihoodLevelId: string,
): { cell: RiskMatrixCellRead; riskLevel: RiskLevelRead } | null {
  if (!severityLevelId || !likelihoodLevelId) {
    return null;
  }

  const cell = cells.find(
    (candidate) =>
      candidate.is_active &&
      candidate.severity_level_id === severityLevelId &&
      candidate.likelihood_level_id === likelihoodLevelId,
  );
  const riskLevel = cell
    ? riskLevels.find((candidate) => candidate.id === cell.risk_level_id)
    : undefined;

  return cell && riskLevel ? { cell, riskLevel } : null;
}

function formatBoolean(value: boolean): string {
  return value ? "Yes" : "No";
}
