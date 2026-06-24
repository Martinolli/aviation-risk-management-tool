import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { createRisk } from "../api/risks";
import { useAuth } from "../auth/AuthContext";

const DOMAIN_OPTIONS = [
  { value: "FLIGHT_TEST", label: "Flight Test" },
  { value: "ENGINEERING", label: "Engineering" },
  { value: "MANUFACTURING", label: "Industrial" },
  { value: "QUALITY", label: "Quality" },
  { value: "SUPPLY_CHAIN", label: "Supply Chain" },
  { value: "MAINTENANCE", label: "Maintenance" },
  { value: "OHSE", label: "Safety (OHSE)" },
  { value: "OTHER", label: "Other" },
] as const;

export function RiskCreatePage() {
  const { isAuthenticated, token } = useAuth();
  const navigate = useNavigate();
  const [problemDescription, setProblemDescription] = useState("");
  const [domain, setDomain] = useState("FLIGHT_TEST");
  const [sourceTrigger, setSourceTrigger] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token) {
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await createRisk(token, {
        problem_description: problemDescription.trim(),
        domain,
        source_trigger: sourceTrigger.trim() || null,
      });
      navigate("/risks", {
        replace: true,
        state: { successMessage: "Risk created successfully." },
      });
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "Unable to create risk.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  return (
    <section className="risk-create-page" aria-labelledby="create-risk-heading">
      <p className="eyebrow">Risk workspace</p>
      <h1 id="create-risk-heading">Create draft risk</h1>
      <p className="create-risk-description">
        Capture the initial problem and domain. Further risk analysis is added
        later in the workflow.
      </p>

      <form className="risk-create-form" onSubmit={handleSubmit}>
        <label htmlFor="problem-description">Problem description</label>
        <textarea
          disabled={isSubmitting}
          id="problem-description"
          name="problem_description"
          onChange={(event) => setProblemDescription(event.target.value)}
          required
          value={problemDescription}
        />

        <label htmlFor="risk-domain">Domain</label>
        <select
          disabled={isSubmitting}
          id="risk-domain"
          name="domain"
          onChange={(event) => setDomain(event.target.value)}
          required
          value={domain}
        >
          {DOMAIN_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <label htmlFor="source-trigger">Source trigger <span>(optional)</span></label>
        <input
          disabled={isSubmitting}
          id="source-trigger"
          name="source_trigger"
          onChange={(event) => setSourceTrigger(event.target.value)}
          type="text"
          value={sourceTrigger}
        />

        {errorMessage && (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        )}

        <div className="form-actions">
          <button disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating risk..." : "Create draft risk"}
          </button>
          <Link className="secondary-link" to="/risks">
            Back to risk records
          </Link>
        </div>
      </form>
    </section>
  );
}
