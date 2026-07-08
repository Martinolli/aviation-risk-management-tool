import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Navigate } from "react-router-dom";

import {
  exportAuditLogsCsv,
  exportAuditLogsDocx,
  listAuditLogs,
} from "../api/auditLogs";
import type { AuditLogListParams } from "../api/auditLogs";
import { ApiError } from "../api/client";
import type { AuditLogRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AuditLogList } from "../components/AuditLogList";
import { saveBlobAsFile } from "../api/reports";

type AuditTrailPageState =
  | { status: "loading" }
  | { status: "success"; auditLogs: AuditLogRead[] }
  | { status: "error"; message: string };

type AuditExportState =
  | { status: "idle" }
  | { status: "loading"; format: "CSV" | "DOCX" }
  | { status: "success"; message: string }
  | { status: "error"; message: string };

interface AuditFilterFormState {
  entityType: string;
  entityId: string;
  action: string;
  changedByUserId: string;
  changedAtFrom: string;
  changedAtTo: string;
  limit: number;
}

const DEFAULT_FILTERS: AuditFilterFormState = {
  entityType: "",
  entityId: "",
  action: "",
  changedByUserId: "",
  changedAtFrom: "",
  changedAtTo: "",
  limit: 100,
};

const ENTITY_TYPES = [
  "RiskRecord",
  "RiskAssessment",
  "RiskAction",
  "RiskDecision",
  "RiskEvidence",
  "RiskMonitoringReview",
  "Committee",
  "CommitteeMember",
  "CommitteeMeeting",
  "GeneratedReport",
  "User",
];

const AUDIT_ACTIONS = [
  "CREATE",
  "UPDATE",
  "ARCHIVE",
  "RESTORE",
  "SUBMIT",
  "APPROVE",
  "REJECT",
  "ESCALATE",
  "RETURN_FOR_REVISION",
  "GENERATE_REPORT",
  "LLM_ANALYSIS",
];

export function AuditTrailPage() {
  const { isAuthenticated, token } = useAuth();
  const [filters, setFilters] = useState<AuditFilterFormState>(DEFAULT_FILTERS);
  const [auditTrailState, setAuditTrailState] = useState<AuditTrailPageState>({
    status: "loading",
  });
  const [exportState, setExportState] = useState<AuditExportState>({
    status: "idle",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    void loadAuditTrail(token, DEFAULT_FILTERS, (nextState) => {
      if (isCurrent) {
        setAuditTrailState(nextState);
      }
    });

    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  const activeFilterCount = getActiveFilterCount(filters);
  const isExporting = exportState.status === "loading";

  async function applyFilters(nextFilters: AuditFilterFormState) {
    if (!token) {
      return;
    }

    setAuditTrailState({ status: "loading" });
    setExportState({ status: "idle" });
    await loadAuditTrail(token, nextFilters, setAuditTrailState);
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

  async function handleExport(format: "CSV" | "DOCX") {
    if (!token) {
      return;
    }

    setExportState({ status: "loading", format });
    try {
      const params = buildAuditLogParams(filters, { exportLimit: true });
      const result =
        format === "CSV"
          ? await exportAuditLogsCsv(token, params)
          : await exportAuditLogsDocx(token, params);
      saveBlobAsFile(result.blob, result.filename);
      setExportState({
        status: "success",
        message: `${format} Audit Trail Export downloaded.`,
      });
    } catch (error) {
      setExportState({
        status: "error",
        message:
          error instanceof ApiError
            ? error.message
            : "Audit Trail Export failed. Please try again.",
      });
    }
  }

  return (
    <section className="audit-trail-page" aria-labelledby="audit-trail-heading">
      <div className="page-header">
        <div>
          <p className="eyebrow">Traceability</p>
          <h1 id="audit-trail-heading">Audit Trail</h1>
          <p>
            Review the latest audit records authorized for your account and
            prepare controlled SMS governance exports.
          </p>
        </div>
      </div>

      <form
        className="audit-filter-panel"
        onSubmit={handleSubmit}
        aria-label="Audit Trail Export filters"
      >
        <div className="risk-table-toolbar">
          <div>
            <h2>Audit Trail Export</h2>
            <p className="audit-filter-summary">
              Controlled Export for Traceability and SMS governance.
            </p>
            <p className="audit-filter-summary">
              {auditTrailState.status === "success"
                ? `Showing ${auditTrailState.auditLogs.length} authorized audit records`
                : "Loading authorized audit records..."}
            </p>
          </div>
          <span className="audit-filter-chip">
            {activeFilterCount} active {activeFilterCount === 1 ? "filter" : "filters"}
          </span>
        </div>

        <div className="audit-filter-grid">
          <label className="audit-filter-field">
            Entity Type
            <select
              value={filters.entityType}
              onChange={(event) =>
                setFilters({ ...filters, entityType: event.target.value })
              }
            >
              <option value="">All</option>
              {ENTITY_TYPES.map((entityType) => (
                <option key={entityType} value={entityType}>
                  {entityType}
                </option>
              ))}
            </select>
          </label>

          <label className="audit-filter-field">
            Entity ID
            <input
              type="text"
              value={filters.entityId}
              onChange={(event) =>
                setFilters({ ...filters, entityId: event.target.value })
              }
            />
          </label>

          <label className="audit-filter-field">
            Action
            <select
              value={filters.action}
              onChange={(event) =>
                setFilters({ ...filters, action: event.target.value })
              }
            >
              <option value="">All</option>
              {AUDIT_ACTIONS.map((action) => (
                <option key={action} value={action}>
                  {action}
                </option>
              ))}
            </select>
          </label>

          <label className="audit-filter-field">
            Changed By User ID
            <input
              type="text"
              value={filters.changedByUserId}
              onChange={(event) =>
                setFilters({ ...filters, changedByUserId: event.target.value })
              }
            />
          </label>

          <div className="audit-date-range">
            <label className="audit-filter-field">
              Changed At From
              <input
                type="datetime-local"
                value={filters.changedAtFrom}
                onChange={(event) =>
                  setFilters({ ...filters, changedAtFrom: event.target.value })
                }
              />
            </label>

            <label className="audit-filter-field">
              Changed At To
              <input
                type="datetime-local"
                value={filters.changedAtTo}
                onChange={(event) =>
                  setFilters({ ...filters, changedAtTo: event.target.value })
                }
              />
            </label>
          </div>

          <label className="audit-filter-field audit-limit-control">
            Limit
            <input
              type="number"
              min={1}
              max={5000}
              value={filters.limit}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  limit: Number(event.target.value || DEFAULT_FILTERS.limit),
                })
              }
            />
          </label>
        </div>

        <div className="audit-filter-actions">
          <button className="button" type="submit">
            Apply Filters
          </button>
          <button className="button secondary" type="button" onClick={handleClearFilters}>
            Clear Filters
          </button>
          <div className="audit-export-actions">
            <button
              className="button secondary"
              disabled={isExporting}
              type="button"
              onClick={() => void handleExport("CSV")}
            >
              {exportState.status === "loading" && exportState.format === "CSV"
                ? "Exporting CSV..."
                : "Export CSV"}
            </button>
            <button
              className="button secondary"
              disabled={isExporting}
              type="button"
              onClick={() => void handleExport("DOCX")}
            >
              {exportState.status === "loading" && exportState.format === "DOCX"
                ? "Exporting DOCX..."
                : "Export DOCX"}
            </button>
          </div>
        </div>

        {exportState.status === "success" && (
          <p className="audit-export-status" role="status">
            {exportState.message}
          </p>
        )}

        {exportState.status === "error" && (
          <p className="audit-export-warning" role="alert">
            {exportState.message}
          </p>
        )}
      </form>

      {auditTrailState.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading audit trail...
        </p>
      )}

      {auditTrailState.status === "error" && (
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong>Unable to load audit trail.</strong>
          <span>{auditTrailState.message}</span>
        </div>
      )}

      {auditTrailState.status === "success" &&
        auditTrailState.auditLogs.length === 0 && (
          <p className="audit-empty">No authorized audit records available.</p>
        )}

      {auditTrailState.status === "success" &&
        auditTrailState.auditLogs.length > 0 && (
          <AuditLogList auditLogs={auditTrailState.auditLogs} />
        )}
    </section>
  );
}

async function loadAuditTrail(
  token: string,
  filters: AuditFilterFormState,
  setAuditTrailState: (state: AuditTrailPageState) => void,
) {
  try {
    const auditLogs = await listAuditLogs(token, buildAuditLogParams(filters));
    setAuditTrailState({ status: "success", auditLogs });
  } catch (error) {
    setAuditTrailState({
      status: "error",
      message:
        error instanceof ApiError ? error.message : "Please try again shortly.",
    });
  }
}

function buildAuditLogParams(
  filters: AuditFilterFormState,
  options: { exportLimit?: boolean } = {},
): AuditLogListParams {
  const limit = Number.isFinite(filters.limit)
    ? filters.limit
    : DEFAULT_FILTERS.limit;

  return {
    entityType: trimOrUndefined(filters.entityType),
    entityId: trimOrUndefined(filters.entityId),
    action: trimOrUndefined(filters.action),
    changedByUserId: trimOrUndefined(filters.changedByUserId),
    changedAtFrom: toApiDateTime(filters.changedAtFrom),
    changedAtTo: toApiDateTime(filters.changedAtTo),
    limit: options.exportLimit ? Math.min(Math.max(limit, 1), 5000) : limit,
  };
}

function trimOrUndefined(value: string): string | undefined {
  const trimmed = value.trim();
  return trimmed ? trimmed : undefined;
}

function toApiDateTime(value: string): string | undefined {
  if (!value) {
    return undefined;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString();
}

function getActiveFilterCount(filters: AuditFilterFormState): number {
  return [
    trimOrUndefined(filters.entityType),
    trimOrUndefined(filters.entityId),
    trimOrUndefined(filters.action),
    trimOrUndefined(filters.changedByUserId),
    filters.changedAtFrom,
    filters.changedAtTo,
    filters.limit !== DEFAULT_FILTERS.limit,
  ].filter(Boolean).length;
}
