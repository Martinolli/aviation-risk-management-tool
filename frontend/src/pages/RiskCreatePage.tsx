import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { listCommittees } from "../api/committees";
import { createRisk } from "../api/risks";
import type { CommitteeRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";

const DOMAIN_OPTIONS = [
  { value: "FLIGHT_TEST", label: "Flight Test" },
  { value: "ENGINEERING", label: "Engineering" },
  { value: "CONTINUED_AIRWORTHINESS", label: "Continued Airworthiness" },
  { value: "MANUFACTURING", label: "Industrial" },
  { value: "PRODUCTION", label: "Production" },
  { value: "QUALITY", label: "Quality" },
  { value: "SUPPLY_CHAIN", label: "Supply Chain" },
  { value: "MAINTENANCE", label: "Maintenance" },
  { value: "SUPPLIER_INTERFACE", label: "Supplier Interface" },
  { value: "OHSE", label: "Safety (OHSE)" },
  { value: "ORGANIZATIONAL", label: "Organizational" },
  { value: "OTHER", label: "Other" },
] as const;

const DOMAIN_BOARD_NAMES: Record<string, string> = {
  FLIGHT_TEST: "Flight Test Safety Committee - Operation",
  ENGINEERING: "Aircraft Safety Committee - Engineering Board",
  CONTINUED_AIRWORTHINESS: "Aircraft Safety Committee - Engineering Board",
  QUALITY:
    "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE",
  MANUFACTURING:
    "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE",
  PRODUCTION:
    "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE",
  SUPPLY_CHAIN:
    "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE",
  OHSE: "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE",
  MAINTENANCE:
    "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE",
  SUPPLIER_INTERFACE:
    "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE",
};

type CommitteeListState =
  | { status: "loading" }
  | { status: "success"; committees: CommitteeRead[] }
  | { status: "error"; message: string };

export function RiskCreatePage() {
  const { isAuthenticated, token } = useAuth();
  const navigate = useNavigate();
  const [problemDescription, setProblemDescription] = useState("");
  const [domain, setDomain] = useState("FLIGHT_TEST");
  const [boardOfOriginId, setBoardOfOriginId] = useState("");
  const [sourceTrigger, setSourceTrigger] = useState("");
  const [committeeList, setCommitteeList] = useState<CommitteeListState>({
    status: "loading",
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadCommitteeOptions() {
      try {
        const committees = await listCommittees(tokenToUse);
        if (isCurrent) {
          setCommitteeList({ status: "success", committees });
        }
      } catch (error) {
        if (isCurrent) {
          setCommitteeList({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadCommitteeOptions();

    return () => {
      isCurrent = false;
    };
  }, [token]);

  useEffect(() => {
    if (committeeList.status !== "success") {
      return;
    }

    setBoardOfOriginId(
      findSuggestedBoardOfOrigin(committeeList.committees, domain)?.id ?? "",
    );
  }, [committeeList, domain]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token) {
      return;
    }

    if (!boardOfOriginId) {
      setErrorMessage("Select the Board of Origin / originating committee.");
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await createRisk(token, {
        problem_description: problemDescription.trim(),
        domain,
        source_trigger: sourceTrigger.trim() || null,
        board_of_origin_id: boardOfOriginId,
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
        Capture the initial problem, domain, and originating committee. Further
        risk analysis is added later in the workflow.
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

        <label htmlFor="board-of-origin">
          Board of Origin / Originating Committee
        </label>
        <select
          disabled={isSubmitting || committeeList.status !== "success"}
          id="board-of-origin"
          name="board_of_origin_id"
          onChange={(event) => setBoardOfOriginId(event.target.value)}
          required
          value={boardOfOriginId}
        >
          <option value="">Select an originating committee</option>
          {committeeList.status === "success" &&
            getOriginatingCommittees(committeeList.committees).map(
              (committee) => (
                <option key={committee.id} value={committee.id}>
                  {committee.name} - {committee.authority_level} -{" "}
                  {committee.committee_type}
                </option>
              ),
            )}
        </select>
        <p className="field-help">
          Suggested from the selected domain. You can choose a different active
          committee when governance ownership requires it.
        </p>

        {committeeList.status === "loading" && (
          <p aria-live="polite" className="field-help" role="status">
            Loading committee options...
          </p>
        )}

        {committeeList.status === "error" && (
          <p className="form-error" role="alert">
            Unable to load committees. {committeeList.message}
          </p>
        )}

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
          <button
            disabled={isSubmitting || committeeList.status !== "success"}
            type="submit"
          >
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

function findSuggestedBoardOfOrigin(
  committees: CommitteeRead[],
  domain: string,
): CommitteeRead | undefined {
  const suggestedName = DOMAIN_BOARD_NAMES[domain];
  return suggestedName
    ? getOriginatingCommittees(committees).find(
        (committee) => committee.name === suggestedName,
      )
    : undefined;
}

function getOriginatingCommittees(
  committees: CommitteeRead[],
): CommitteeRead[] {
  return committees.filter(
    (committee) =>
      committee.authority_level === "LOW" &&
      committee.committee_type === "OPERATIONAL_BOARD",
  );
}
