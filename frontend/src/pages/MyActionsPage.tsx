import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { listMyRiskActions } from "../api/riskActions";
import type { RiskActionRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import {
  compareRiskActionsByUrgency,
  getRiskActionDueStatus,
  getRiskActionDueStatusLabel,
  getRiskActionDueStatusTone,
  isRiskActionOpen,
  type RiskActionDueStatus,
} from "../utils/actionDueStatus";

type MyActionsState =
  | { status: "loading" }
  | { status: "success"; actions: RiskActionRead[] }
  | { status: "error"; message: string };

export function MyActionsPage() {
  const { isAuthenticated, token } = useAuth();
  const [includeCompleted, setIncludeCompleted] = useState(false);
  const [includeCancelled, setIncludeCancelled] = useState(false);
  const [actionsState, setActionsState] = useState<MyActionsState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;
    if (!token) {
      return;
    }
    const tokenToUse = token;

    async function loadActions() {
      setActionsState({ status: "loading" });
      try {
        const actions = await listMyRiskActions(tokenToUse, {
          includeCompleted,
          includeCancelled,
        });
        if (isCurrent) {
          setActionsState({
            status: "success",
            actions: [...actions].sort(compareRiskActionsByUrgency),
          });
        }
      } catch (error) {
        if (isCurrent) {
          setActionsState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadActions();
    return () => {
      isCurrent = false;
    };
  }, [includeCancelled, includeCompleted, token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  const actions = actionsState.status === "success" ? actionsState.actions : [];
  const statuses = actions.map((action) => getRiskActionDueStatus(action));

  return (
    <section className="actions-page" aria-labelledby="my-actions-heading">
      <header className="page-header">
        <div>
          <p className="eyebrow">Mitigation follow-up</p>
          <h1 id="my-actions-heading">My Actions</h1>
          <p>
            Track mitigation and risk control actions assigned to you or visible
            through your authorized risk access.
          </p>
        </div>
      </header>

      <section aria-label="Risk Action counts" className="action-kpi-grid">
        <ActionKpi
          label="Overdue"
          tone="overdue"
          value={countStatus(statuses, "OVERDUE")}
        />
        <ActionKpi
          label="Due today"
          tone="due-today"
          value={countStatus(statuses, "DUE_TODAY")}
        />
        <ActionKpi
          label="Due soon"
          tone="due-soon"
          value={countStatus(statuses, "DUE_SOON")}
        />
        <ActionKpi
          label="Open / no due date"
          tone="open"
          value={
            countStatus(statuses, "OPEN") +
            countStatus(statuses, "NO_DUE_DATE")
          }
        />
        {includeCompleted && (
          <ActionKpi
            label="Completed"
            tone="completed"
            value={countStatus(statuses, "COMPLETED")}
          />
        )}
      </section>

      <div className="action-filter-bar">
        <label>
          <input
            checked={includeCompleted}
            onChange={(event) => setIncludeCompleted(event.target.checked)}
            type="checkbox"
          />
          Include completed actions
        </label>
        <label>
          <input
            checked={includeCancelled}
            onChange={(event) => setIncludeCancelled(event.target.checked)}
            type="checkbox"
          />
          Include cancelled actions
        </label>
      </div>

      {actionsState.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading My Actions...
        </p>
      )}
      {actionsState.status === "error" && (
        <div className="workspace-alert" role="alert">
          <strong>Unable to load My Actions.</strong>
          <span>{actionsState.message}</span>
        </div>
      )}
      {actionsState.status === "success" && actions.length === 0 && (
        <p className="action-empty">No open actions assigned or visible.</p>
      )}
      {actionsState.status === "success" && actions.length > 0 && (
        <div className="action-table-wrapper">
          <table className="action-queue-table">
            <caption className="visually-hidden">
              Risk Actions visible to the current user
            </caption>
            <thead>
              <tr>
                <th scope="col">Due status</th>
                <th scope="col">Risk Action</th>
                <th scope="col">Due Date</th>
                <th scope="col">Status</th>
                <th scope="col">Action Owner</th>
                <th scope="col">Risk</th>
                <th scope="col">Completion</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((action) => (
                <ActionRow action={action} key={action.id} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ActionKpi({
  label,
  tone,
  value,
}: {
  label: string;
  tone: string;
  value: number;
}) {
  return (
    <article className={`action-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function ActionRow({ action }: { action: RiskActionRead }) {
  const dueStatus = getRiskActionDueStatus(action);
  const riskRecordId = action.risk_record_id;

  return (
    <tr className={`action-row ${getRiskActionDueStatusTone(dueStatus)}`}>
      <td>
        <ActionDueBadge status={dueStatus} />
      </td>
      <td>
        <strong>{action.title || "Untitled action"}</strong>
        <span className="action-description-excerpt">
          {excerpt(action.description) || "No description provided."}
        </span>
      </td>
      <td>{action.due_date || "Not scheduled"}</td>
      <td>{formatLabel(action.status) || "Not specified"}</td>
      <td>{action.action_owner_user_id || "Not assigned"}</td>
      <td>
        {riskRecordId ? (
          <Link to={`/risks/${riskRecordId}`}>{riskRecordId.slice(0, 8)}</Link>
        ) : (
          "Not available"
        )}
      </td>
      <td>
        <div className="action-description-excerpt">
          <span>Completed At: {formatDateTime(action.completed_at)}</span>
          {action.completion_notes && (
            <span>Notes: {excerpt(action.completion_notes)}</span>
          )}
        </div>
      </td>
      <td>
        <div className="action-row-links">
          {riskRecordId && (
            <Link className="secondary-link" to={`/risks/${riskRecordId}`}>
              Open risk detail
            </Link>
          )}
          {riskRecordId && isRiskActionOpen(action) && (
            <Link
              className="secondary-link"
              to={`/risks/${riskRecordId}/actions/${action.id}/complete`}
            >
              Complete action
            </Link>
          )}
        </div>
      </td>
    </tr>
  );
}

function ActionDueBadge({ status }: { status: RiskActionDueStatus }) {
  return (
    <span className={`action-due-badge ${getRiskActionDueStatusTone(status)}`}>
      {getRiskActionDueStatusLabel(status)}
    </span>
  );
}

function countStatus(
  statuses: RiskActionDueStatus[],
  status: RiskActionDueStatus,
): number {
  return statuses.filter((value) => value === status).length;
}

function excerpt(value: string | null | undefined, limit = 100): string {
  const normalized = value?.trim() ?? "";
  return normalized.length > limit
    ? `${normalized.slice(0, limit).trimEnd()}…`
    : normalized;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not completed";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? "Not completed"
    : parsed.toLocaleString();
}

function formatLabel(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
