import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import { ApiError } from "../api/client";
import { listCommittees } from "../api/committees";
import { listRisks } from "../api/risks";
import type { RiskListParams } from "../api/risks";
import type { CommitteeRead, RiskRecordRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import {
  getRiskPackageStatusLabel,
  getRiskPackageStatusTone,
} from "../utils/riskReadiness";

type RiskListState =
  | { status: "loading" }
  | {
      status: "success";
      risks: RiskRecordRead[];
      committees: CommitteeRead[];
      committeeWarning: string | null;
    }
  | { status: "error"; message: string };

const DEFAULT_FILTERS: RiskListParams = {
  includeArchived: false,
  search: "",
  riskId: "",
  domain: "",
  boardOfOriginId: "",
  workflowStatus: "",
  lifecycleStatus: "",
  ownerUserId: "",
  createdByUserId: "",
  latestRiskLevel: "",
  hasOverdueActions: null,
  hasDueOrOverdueMonitoring: null,
  sortBy: "updated_at",
  sortDirection: "desc",
};

const RISK_DOMAINS = [
  "FLIGHT_TEST",
  "ENGINEERING",
  "MANUFACTURING",
  "QUALITY",
  "PRODUCTION",
  "SUPPLY_CHAIN",
  "OHSE",
  "CONTINUED_AIRWORTHINESS",
  "MAINTENANCE",
  "SUPPLIER_INTERFACE",
  "ORGANIZATIONAL",
  "OTHER",
];

const WORKFLOW_STATUSES = [
  "DRAFT",
  "SUBMITTED_TO_OPERATIONAL_BOARD",
  "UNDER_OPERATIONAL_BOARD_REVIEW",
  "APPROVED_AT_OPERATIONAL_BOARD",
  "ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE",
  "UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW",
  "APPROVED_AT_RISK_MANAGEMENT_COMMITTEE",
  "ESCALATED_TO_EXECUTIVE_COMMITTEE",
  "UNDER_EXECUTIVE_COMMITTEE_REVIEW",
  "ACCEPTED",
  "REJECTED",
  "RETURNED_FOR_REVISION",
  "CLOSED",
];

const LIFECYCLE_STATUSES = [
  "OPEN",
  "UNDER_ANALYSIS",
  "PENDING_MITIGATION",
  "MITIGATION_IN_PROGRESS",
  "PENDING_RESIDUAL_RISK_REVIEW",
  "PENDING_ACCEPTANCE",
  "MONITORING",
  "CLOSED",
];

const SORT_OPTIONS = [
  { value: "updated_at", label: "Updated date" },
  { value: "created_at", label: "Created date" },
  { value: "risk_id", label: "Risk ID" },
  { value: "domain", label: "Domain" },
  { value: "workflow_status", label: "Workflow Status" },
  { value: "lifecycle_status", label: "Lifecycle Status" },
];

export function RiskListPage() {
  const { isAuthenticated, token } = useAuth();
  const location = useLocation();
  const [filters, setFilters] = useState<RiskListParams>(DEFAULT_FILTERS);
  const [riskList, setRiskList] = useState<RiskListState>({ status: "loading" });
  const successMessage = getSuccessMessage(location.state);

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    void loadRiskList(token, DEFAULT_FILTERS, (nextState) => {
      if (isCurrent) {
        setRiskList(nextState);
      }
    });

    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  const committees = riskList.status === "success" ? riskList.committees : [];
  const activeFilterCount = getActiveFilterCount(filters);

  async function applyFilters(nextFilters: RiskListParams) {
    if (!token) {
      return;
    }

    setRiskList({ status: "loading" });
    await loadRiskList(token, nextFilters, setRiskList);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void applyFilters(filters);
  }

  function handleClearFilters() {
    const resetFilters = { ...DEFAULT_FILTERS };
    setFilters(resetFilters);
    void applyFilters(resetFilters);
  }

  return (
    <section className="workspace-page" aria-labelledby="risk-list-heading">
      <div className="page-header">
        <div>
          <p className="eyebrow">Risk workspace</p>
          <h1 id="risk-list-heading">Risk Records</h1>
          <p>
            Review the risk records authorized for your account and their
            originating committees.
          </p>
        </div>
        <Link className="button" to="/risks/new">
          Create Risk
        </Link>
      </div>

      {successMessage && (
        <p aria-live="polite" className="workspace-success" role="status">
          {successMessage}
        </p>
      )}

      {riskList.status === "success" && riskList.committeeWarning && (
        <p className="audit-warning" role="status">
          {riskList.committeeWarning}
        </p>
      )}

      <form
        className="risk-filter-panel"
        onSubmit={handleSubmit}
        aria-label="Advanced Filters"
      >
        <div className="risk-table-toolbar">
          <div>
            <h2>Advanced Filters</h2>
            <p className="risk-filter-summary">
              {riskList.status === "success"
                ? `Showing ${riskList.risks.length} risk records`
                : "Loading risk records..."}
            </p>
          </div>
          <span className="risk-filter-count">
            {activeFilterCount} active {activeFilterCount === 1 ? "filter" : "filters"}
          </span>
        </div>

        <div className="risk-filter-grid">
          <label className="risk-filter-field risk-filter-wide">
            Search
            <input
              className="risk-search-input"
              type="search"
              placeholder="Search Risk ID, problem description, hazard, central event..."
              value={filters.search ?? ""}
              onChange={(event) =>
                setFilters({ ...filters, search: event.target.value })
              }
            />
          </label>

          <label className="risk-filter-field">
            Risk ID
            <input
              type="text"
              placeholder="RISK-2026-0001"
              value={filters.riskId ?? ""}
              onChange={(event) =>
                setFilters({ ...filters, riskId: event.target.value })
              }
            />
          </label>

          <label className="risk-filter-field">
            Domain
            <select
              value={filters.domain ?? ""}
              onChange={(event) =>
                setFilters({ ...filters, domain: event.target.value })
              }
            >
              <option value="">All domains</option>
              {RISK_DOMAINS.map((domain) => (
                <option key={domain} value={domain}>
                  {domain}
                </option>
              ))}
            </select>
          </label>

          <label className="risk-filter-field">
            Board of Origin
            <select
              value={filters.boardOfOriginId ?? ""}
              onChange={(event) =>
                setFilters({ ...filters, boardOfOriginId: event.target.value })
              }
            >
              <option value="">All boards</option>
              {committees.map((committee) => (
                <option key={committee.id} value={committee.id}>
                  {committee.name} ({committee.authority_level} Authority Level)
                </option>
              ))}
            </select>
          </label>

          <label className="risk-filter-field">
            Workflow Status
            <select
              value={filters.workflowStatus ?? ""}
              onChange={(event) =>
                setFilters({ ...filters, workflowStatus: event.target.value })
              }
            >
              <option value="">All workflow statuses</option>
              {WORKFLOW_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>

          <label className="risk-filter-field">
            Lifecycle Status
            <select
              value={filters.lifecycleStatus ?? ""}
              onChange={(event) =>
                setFilters({ ...filters, lifecycleStatus: event.target.value })
              }
            >
              <option value="">All lifecycle statuses</option>
              {LIFECYCLE_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>

          <label className="risk-filter-field">
            Latest/Recorded Risk Level
            <input
              type="text"
              placeholder="LOW, MEDIUM, HIGH, EXTREME"
              value={filters.latestRiskLevel ?? ""}
              onChange={(event) =>
                setFilters({ ...filters, latestRiskLevel: event.target.value })
              }
            />
          </label>

          <label className="risk-filter-field">
            Overdue Actions
            <select
              value={booleanFilterToValue(filters.hasOverdueActions)}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  hasOverdueActions: valueToBooleanFilter(event.target.value),
                })
              }
            >
              <option value="any">Any</option>
              <option value="true">Has overdue actions</option>
              <option value="false">No overdue actions</option>
            </select>
          </label>

          <label className="risk-filter-field">
            Monitoring Due
            <select
              value={booleanFilterToValue(filters.hasDueOrOverdueMonitoring)}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  hasDueOrOverdueMonitoring: valueToBooleanFilter(
                    event.target.value,
                  ),
                })
              }
            >
              <option value="any">Any</option>
              <option value="true">Has due/overdue monitoring</option>
              <option value="false">No due/overdue monitoring</option>
            </select>
          </label>

          <label className="risk-filter-field">
            Sort By
            <select
              value={filters.sortBy ?? "updated_at"}
              onChange={(event) =>
                setFilters({ ...filters, sortBy: event.target.value })
              }
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="risk-filter-field">
            Sort Direction
            <select
              value={filters.sortDirection ?? "desc"}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  sortDirection: event.target.value as "asc" | "desc",
                })
              }
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
        </div>

        <div className="risk-filter-compact-row">
          <label>
            <input
              type="checkbox"
              checked={!!filters.includeArchived}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  includeArchived: event.target.checked,
                })
              }
            />
            Include archived
          </label>
        </div>

        {activeFilterCount > 0 && (
          <div className="risk-filter-summary" aria-live="polite">
            <span className="risk-filter-chip">
              {activeFilterCount} active {activeFilterCount === 1 ? "filter" : "filters"}
            </span>
          </div>
        )}

        <div className="risk-filter-actions">
          <button className="button" type="submit">
            Apply Filters
          </button>
          <button className="button secondary" type="button" onClick={handleClearFilters}>
            Clear Filters
          </button>
        </div>
      </form>

      {riskList.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading risk records...
        </p>
      )}

      {riskList.status === "error" && (
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong>Unable to load risk records.</strong>
          <span>{riskList.message}</span>
        </div>
      )}

      {riskList.status === "success" && riskList.risks.length === 0 && (
        <section className="workspace-empty" aria-labelledby="empty-risks-heading">
          <h2 id="empty-risks-heading">No risk records found yet.</h2>
          <p>Create the first draft risk to begin the workflow.</p>
        </section>
      )}

      {riskList.status === "success" && riskList.risks.length > 0 && (
        <div className="risk-table-wrapper">
          <table className="risk-table">
            <caption className="visually-hidden">Available risk records</caption>
            <thead>
              <tr>
                <th scope="col">Risk ID</th>
                <th scope="col">Domain</th>
                <th scope="col">Board of Origin</th>
                <th scope="col">Workflow Status</th>
                <th scope="col">Readiness</th>
                <th scope="col">Problem description</th>
                <th scope="col">Updated</th>
              </tr>
            </thead>
            <tbody>
              {riskList.risks.map((risk) => {
                const readinessLabel = getRiskPackageStatusLabel(risk);
                const readinessTone = getRiskPackageStatusTone(risk);

                return (
                  <tr key={risk.id}>
                    <td className="risk-id">
                      <Link className="risk-detail-link" to={`/risks/${risk.id}`}>
                        {getRiskDisplayId(risk)}
                      </Link>
                    </td>
                    <td>{risk.domain}</td>
                    <td className="risk-board-origin">
                      {getBoardOfOriginLabel(risk, riskList.committees)}
                    </td>
                    <td>
                      <span className="status-badge">{getRiskStatus(risk)}</span>
                    </td>
                    <td>
                      <div className="readiness-cell">
                        <span className={`readiness-badge ${readinessTone}`}>
                          {readinessLabel}
                        </span>
                        {risk.workflow_status === "DRAFT" && (
                          <span className="readiness-hint">
                            {readinessLabel === "Package complete"
                              ? "Open detail to confirm assessment readiness."
                              : "Open detail to review missing items."}
                          </span>
                        )}
                      </div>
                    </td>
                    <td
                      className="risk-description"
                      title={risk.problem_description}
                    >
                      {risk.problem_description}
                    </td>
                    <td className="muted-text">{getRiskDate(risk)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

async function loadRiskList(
  token: string,
  filters: RiskListParams,
  setRiskList: (state: RiskListState) => void,
) {
  const [riskResult, committeeResult] = await Promise.allSettled([
    listRisks(token, normalizeRiskListParams(filters)),
    listCommittees(token),
  ]);

  if (riskResult.status === "rejected") {
    setRiskList({
      status: "error",
      message:
        riskResult.reason instanceof ApiError
          ? riskResult.reason.message
          : "Please try again shortly.",
    });
    return;
  }

  setRiskList({
    status: "success",
    risks: riskResult.value,
    committees: committeeResult.status === "fulfilled" ? committeeResult.value : [],
    committeeWarning:
      committeeResult.status === "rejected"
        ? "Committee names could not be loaded. Board of Origin IDs are shown instead."
        : null,
  });
}

function normalizeRiskListParams(filters: RiskListParams): RiskListParams {
  return {
    includeArchived: filters.includeArchived,
    search: trimOrUndefined(filters.search),
    riskId: trimOrUndefined(filters.riskId),
    domain: trimOrUndefined(filters.domain),
    boardOfOriginId: trimOrUndefined(filters.boardOfOriginId),
    workflowStatus: trimOrUndefined(filters.workflowStatus),
    lifecycleStatus: trimOrUndefined(filters.lifecycleStatus),
    ownerUserId: trimOrUndefined(filters.ownerUserId),
    createdByUserId: trimOrUndefined(filters.createdByUserId),
    latestRiskLevel: trimOrUndefined(filters.latestRiskLevel),
    hasOverdueActions: filters.hasOverdueActions,
    hasDueOrOverdueMonitoring: filters.hasDueOrOverdueMonitoring,
    sortBy: filters.sortBy || "updated_at",
    sortDirection: filters.sortDirection || "desc",
  };
}

function trimOrUndefined(value: string | undefined): string | undefined {
  const trimmed = value?.trim();
  return trimmed ? trimmed : undefined;
}

function getActiveFilterCount(filters: RiskListParams): number {
  const normalizedFilters = normalizeRiskListParams(filters);
  return [
    normalizedFilters.search,
    normalizedFilters.riskId,
    normalizedFilters.domain,
    normalizedFilters.boardOfOriginId,
    normalizedFilters.workflowStatus,
    normalizedFilters.lifecycleStatus,
    normalizedFilters.ownerUserId,
    normalizedFilters.createdByUserId,
    normalizedFilters.latestRiskLevel,
    normalizedFilters.hasOverdueActions !== null &&
      normalizedFilters.hasOverdueActions !== undefined,
    normalizedFilters.hasDueOrOverdueMonitoring !== null &&
      normalizedFilters.hasDueOrOverdueMonitoring !== undefined,
    normalizedFilters.includeArchived,
    normalizedFilters.sortBy !== "updated_at",
    normalizedFilters.sortDirection !== "desc",
  ].filter(Boolean).length;
}

function booleanFilterToValue(value: boolean | null | undefined): string {
  if (value === true) {
    return "true";
  }
  if (value === false) {
    return "false";
  }
  return "any";
}

function valueToBooleanFilter(value: string): boolean | null {
  if (value === "true") {
    return true;
  }
  if (value === "false") {
    return false;
  }
  return null;
}

export function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

export function getRiskStatus(risk: RiskRecordRead): string {
  return risk.workflow_status || risk.lifecycle_status || "Unknown";
}

function getBoardOfOriginLabel(
  risk: RiskRecordRead,
  committees: CommitteeRead[],
): string {
  if (!risk.board_of_origin_id) {
    return "Not assigned";
  }

  return (
    committees.find((committee) => committee.id === risk.board_of_origin_id)
      ?.name ?? risk.board_of_origin_id
  );
}

function getRiskDate(risk: RiskRecordRead): string {
  const date = new Date(risk.updated_at || risk.created_at);

  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleDateString();
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
