import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getRiskDetail, updateRisk } from "../api/risks";
import type { RiskDetailResponse, RiskRecordRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RiskPackageEditState =
  | { status: "loading" }
  | { status: "success"; risk: RiskRecordRead }
  | { status: "error"; message: string };

interface RiskPackageFormState {
  systemScope: string;
  centralEvent: string;
  hazardStatement: string;
  causes: string;
  consequences: string;
  existingControls: string;
}

const EMPTY_FORM: RiskPackageFormState = {
  systemScope: "",
  centralEvent: "",
  hazardStatement: "",
  causes: "",
  consequences: "",
  existingControls: "",
};

export function RiskPackageEditPage() {
  const { isAuthenticated, token } = useAuth();
  const { riskRecordId } = useParams();
  const navigate = useNavigate();
  const [pageState, setPageState] = useState<RiskPackageEditState>({
    status: "loading",
  });
  const [form, setForm] = useState<RiskPackageFormState>(EMPTY_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    if (!token || !riskRecordId) {
      return;
    }

    const tokenToUse = token;
    const idToLoad = riskRecordId;

    async function loadRiskPackage() {
      try {
        const detail = await getRiskDetail(tokenToUse, idToLoad);
        const risk = getRiskRecord(detail);
        if (!risk) {
          throw new Error("The API response did not include a risk record.");
        }
        if (isCurrent) {
          setPageState({ status: "success", risk });
          setForm(toFormState(risk));
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }
        setPageState({
          status: "error",
          message:
            error instanceof ApiError || error instanceof Error
              ? error.message
              : "Please try again shortly.",
        });
      }
    }

    void loadRiskPackage();
    return () => {
      isCurrent = false;
    };
  }, [riskRecordId, token]);

  function updateField(field: keyof RiskPackageFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !riskRecordId || pageState.status !== "success") {
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      await updateRisk(token, riskRecordId, {
        system_scope: toNullableText(form.systemScope),
        central_event: toNullableText(form.centralEvent),
        hazard_statement: toNullableText(form.hazardStatement),
        causes: toNullableLines(form.causes),
        consequences: toNullableLines(form.consequences),
        existing_controls: toNullableLines(form.existingControls),
      });
      navigate(`/risks/${riskRecordId}`, {
        replace: true,
        state: { successMessage: "Risk package updated successfully." },
      });
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to update the risk package. Please try again.",
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
        Loading risk package...
      </p>
    );
  }

  if (pageState.status === "error") {
    return (
      <section className="risk-package-edit-page" aria-labelledby="package-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="package-load-error">Unable to load risk package.</strong>
          <span>{pageState.message}</span>
        </div>
      </section>
    );
  }

  const risk = pageState.risk;

  return (
    <section className="risk-package-edit-page" aria-labelledby="package-edit-heading">
      <Link className="back-link" to={`/risks/${risk.id}`}>
        Back to risk detail
      </Link>
      <div>
        <p className="eyebrow">Risk workspace</p>
        <h1 id="package-edit-heading">Complete risk package</h1>
        <p className="risk-package-description">
          Add the structured risk context used by assessment, governance review,
          and the Risk Dossier Report.
        </p>
      </div>

      <section className="risk-package-context-card" aria-labelledby="package-context-heading">
        <h2 id="package-context-heading">Risk context</h2>
        <dl className="metadata-grid">
          <div>
            <dt>Risk ID</dt>
            <dd>{risk.risk_id || risk.id}</dd>
          </div>
          <div>
            <dt>Domain</dt>
            <dd>{risk.domain}</dd>
          </div>
          <div>
            <dt>Board of Origin / Originating Committee</dt>
            <dd>{risk.board_of_origin_id || "Not assigned"}</dd>
          </div>
          <div>
            <dt>Workflow status</dt>
            <dd>{risk.workflow_status}</dd>
          </div>
        </dl>
        <div className="risk-package-problem-context">
          <h3>Problem description</h3>
          <p>{risk.problem_description}</p>
        </div>
      </section>

      <form className="risk-package-form" onSubmit={handleSubmit}>
        <label htmlFor="system-scope">System Scope</label>
        <textarea
          disabled={isSubmitting}
          id="system-scope"
          onChange={(event) => updateField("systemScope", event.target.value)}
          placeholder="Describe the aircraft, system, operation, process, or organizational scope affected by this risk."
          value={form.systemScope}
        />

        <label htmlFor="central-event">Central Event</label>
        <textarea
          disabled={isSubmitting}
          id="central-event"
          onChange={(event) => updateField("centralEvent", event.target.value)}
          placeholder="Describe the central event or undesired state around which the risk is organized."
          value={form.centralEvent}
        />

        <label htmlFor="hazard-statement">Hazard Statement</label>
        <textarea
          disabled={isSubmitting}
          id="hazard-statement"
          onChange={(event) => updateField("hazardStatement", event.target.value)}
          placeholder="Describe the hazard in a clear condition/consequence-oriented statement."
          value={form.hazardStatement}
        />

        <label htmlFor="causes">Causes</label>
        <textarea
          aria-describedby="causes-help"
          disabled={isSubmitting}
          id="causes"
          onChange={(event) => updateField("causes", event.target.value)}
          placeholder="Enter one cause per line."
          value={form.causes}
        />
        <p className="field-help" id="causes-help">Enter one cause per line.</p>

        <label htmlFor="consequences">Consequences</label>
        <textarea
          aria-describedby="consequences-help"
          disabled={isSubmitting}
          id="consequences"
          onChange={(event) => updateField("consequences", event.target.value)}
          placeholder="Enter one consequence per line."
          value={form.consequences}
        />
        <p className="field-help" id="consequences-help">
          Enter one consequence per line.
        </p>

        <label htmlFor="existing-controls">Existing Controls</label>
        <textarea
          aria-describedby="existing-controls-help"
          disabled={isSubmitting}
          id="existing-controls"
          onChange={(event) => updateField("existingControls", event.target.value)}
          placeholder="Enter one existing control per line."
          value={form.existingControls}
        />
        <p className="field-help" id="existing-controls-help">
          Enter one existing control per line.
        </p>

        {errorMessage && (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        )}

        <div className="form-actions">
          <button disabled={isSubmitting} type="submit">
            {isSubmitting ? "Saving risk package..." : "Save risk package"}
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

function toFormState(risk: RiskRecordRead): RiskPackageFormState {
  return {
    systemScope: risk.system_scope || "",
    centralEvent: risk.central_event || "",
    hazardStatement: risk.hazard_statement || "",
    causes: (risk.causes ?? []).join("\n"),
    consequences: (risk.consequences ?? []).join("\n"),
    existingControls: (risk.existing_controls ?? []).join("\n"),
  };
}

function toNullableText(value: string): string | null {
  return value.trim() || null;
}

function toNullableLines(value: string): string[] | null {
  const entries = value
    .split(/\r?\n/)
    .map((entry) => entry.trim())
    .filter(Boolean);
  return entries.length > 0 ? entries : null;
}
