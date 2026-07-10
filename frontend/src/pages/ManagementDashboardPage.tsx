import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { getManagementDashboard } from "../api/managementDashboard";
import type {
  ManagementDashboardAttentionItem,
  ManagementDashboardGroup,
  ManagementDashboardRead,
  ManagementDashboardRiskSummary,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type ManagementDashboardState =
  | { status: "loading" }
  | { status: "success"; dashboard: ManagementDashboardRead }
  | { status: "error"; message: string };

const KPI_ORDER = [
  "total_open_risks",
  "high_risk_exposure",
  "escalated_risks",
  "accepted_monitoring",
  "overdue_actions",
  "monitoring_concerns",
  "committee_backlog",
  "draft_package_backlog",
];

export function ManagementDashboardPage() {
  const { isAuthenticated, token } = useAuth();
  const [dashboardState, setDashboardState] =
    useState<ManagementDashboardState>({ status: "loading" });

  useEffect(() => {
    let isCurrent = true;
    if (!token) {
      return;
    }
    const tokenToUse = token;

    async function loadManagementDashboard() {
      setDashboardState({ status: "loading" });
      try {
        const dashboard = await getManagementDashboard(tokenToUse, { limit: 10 });
        if (isCurrent) {
          setDashboardState({ status: "success", dashboard });
        }
      } catch (error) {
        if (isCurrent) {
          setDashboardState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadManagementDashboard();
    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (dashboardState.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading Management Dashboard...
      </p>
    );
  }

  if (dashboardState.status === "error") {
    return (
      <section
        className="management-dashboard-page"
        aria-labelledby="management-dashboard-error"
      >
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="management-dashboard-error">
            Unable to load Management Dashboard.
          </strong>
          <span>{dashboardState.message}</span>
        </div>
      </section>
    );
  }

  const dashboard = dashboardState.dashboard;

  return (
    <section
      className="management-dashboard-page"
      aria-labelledby="management-dashboard-heading"
    >
      <header className="page-header">
        <div>
          <p className="eyebrow">Executive Summary</p>
          <h1 id="management-dashboard-heading">Management Dashboard</h1>
          <p>
            Executive summary of risk exposure, governance backlog, overdue
            controls, and monitoring concerns.
          </p>
        </div>
      </header>

      <section
        className="management-kpi-grid"
        aria-label="Executive Summary KPI grid"
      >
        {[...dashboard.kpis]
          .sort((first, second) => KPI_ORDER.indexOf(first.key) - KPI_ORDER.indexOf(second.key))
          .map((kpi) => (
            <article
              className={`management-kpi-card ${severityClass(kpi.severity)}`}
              key={kpi.key}
            >
              <span>{kpi.label}</span>
              <strong>{kpi.value}</strong>
              {kpi.detail && <small>{kpi.detail}</small>}
            </article>
          ))}
      </section>

      <section className="management-section" aria-labelledby="needs-attention-heading">
        <SectionHeader
          eyebrow="Needs Attention"
          title="Governance Follow-up"
          meta={formatGeneratedAt(dashboard.generated_at)}
        />
        {dashboard.top_attention_items.length === 0 ? (
          <p className="management-empty">No notifications requiring attention.</p>
        ) : (
          <div className="management-attention-list">
            {dashboard.top_attention_items.map((item) => (
              <AttentionCard item={item} key={`${item.category}:${item.target_id}`} />
            ))}
          </div>
        )}
      </section>

      <section className="management-section" aria-labelledby="high-risk-heading">
        <SectionHeader eyebrow="High Risk Exposure" title="High Risk Exposure" />
        <RiskTable
          emptyMessage="No high exposure risks."
          risks={dashboard.high_exposure_risks}
        />
      </section>

      <div className="management-backlog-grid">
        <section className="management-section" aria-labelledby="domain-hotspots-heading">
          <SectionHeader eyebrow="Domain Hotspots" title="Domain Hotspots" />
          <GroupBars groups={dashboard.domain_hotspots} />
        </section>
        <section className="management-section" aria-labelledby="risk-level-heading">
          <SectionHeader eyebrow="Exposure mix" title="Risk level distribution" />
          <GroupBars groups={dashboard.risk_level_distribution} />
        </section>
      </div>

      <div className="management-backlog-grid">
        <section className="management-section" aria-labelledby="workflow-backlog-heading">
          <SectionHeader eyebrow="Committee Backlog" title="Workflow backlog" />
          <GroupList groups={dashboard.workflow_backlog} />
        </section>
        <section className="management-section" aria-labelledby="authority-backlog-heading">
          <SectionHeader eyebrow="Authority Level" title="Authority Level backlog" />
          <GroupList groups={dashboard.authority_level_backlog} />
        </section>
      </div>

      <section className="management-section" aria-labelledby="overdue-actions-heading">
        <SectionHeader eyebrow="Overdue Actions" title="Overdue Actions" />
        <RiskTable
          emptyMessage="No overdue actions."
          risks={dashboard.overdue_action_risks}
        />
      </section>

      <section className="management-section" aria-labelledby="monitoring-heading">
        <SectionHeader eyebrow="Monitoring Concerns" title="Monitoring Concerns" />
        <RiskTable
          emptyMessage="No monitoring concerns."
          risks={dashboard.monitoring_concern_risks}
        />
      </section>

      <section className="management-section" aria-labelledby="committee-backlog-heading">
        <SectionHeader eyebrow="Committee Backlog" title="Committee Backlog" />
        <RiskTable
          emptyMessage="No committee backlog."
          risks={dashboard.committee_backlog_risks}
        />
      </section>
    </section>
  );
}

function SectionHeader({
  eyebrow,
  title,
  meta,
}: {
  eyebrow: string;
  title: string;
  meta?: string;
}) {
  return (
    <div className="management-section-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {meta && <span>{meta}</span>}
    </div>
  );
}

function AttentionCard({ item }: { item: ManagementDashboardAttentionItem }) {
  return (
    <article className="management-attention-card">
      <div>
        <span className={`management-severity-badge ${severityClass(item.severity)}`}>
          {formatLabel(item.severity)}
        </span>
        <span className="management-category-badge">{formatLabel(item.category)}</span>
      </div>
      <h3>{item.title}</h3>
      <p>{item.message}</p>
      {item.due_date && <small>Due date: {item.due_date}</small>}
      {item.action_url && (
        <Link className="secondary-link" to={item.action_url}>
          Open
        </Link>
      )}
    </article>
  );
}

function RiskTable({
  risks,
  emptyMessage,
}: {
  risks: ManagementDashboardRiskSummary[];
  emptyMessage: string;
}) {
  if (risks.length === 0) {
    return <p className="management-empty">{emptyMessage}</p>;
  }

  return (
    <div className="management-risk-table-wrapper">
      <table className="management-risk-table">
        <thead>
          <tr>
            <th scope="col">Risk ID</th>
            <th scope="col">Domain</th>
            <th scope="col">Latest Risk Level</th>
            <th scope="col">Workflow Status</th>
            <th scope="col">Lifecycle Status</th>
            <th scope="col">Board of Origin</th>
            <th scope="col">Updated</th>
            <th scope="col">Open link</th>
          </tr>
        </thead>
        <tbody>
          {risks.map((risk) => (
            <tr key={risk.risk_record_id}>
              <td>{risk.risk_id || risk.risk_record_id.slice(0, 8)}</td>
              <td>{formatLabel(risk.domain)}</td>
              <td>{risk.latest_risk_level || "Not assessed"}</td>
              <td>{formatLabel(risk.workflow_status)}</td>
              <td>{formatLabel(risk.lifecycle_status)}</td>
              <td>{risk.board_of_origin_name || "Not assigned"}</td>
              <td>{formatDate(risk.updated_at)}</td>
              <td>
                <Link className="secondary-link" to={`/risks/${risk.risk_record_id}`}>
                  Open
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GroupBars({ groups }: { groups: ManagementDashboardGroup[] }) {
  const total = groups.reduce((sum, group) => sum + group.count, 0);
  if (groups.length === 0) {
    return <p className="management-empty">No data available.</p>;
  }
  return (
    <ul className="management-hotspot-list">
      {groups.map((group) => {
        const percentage = total > 0 ? Math.round((group.count / total) * 100) : 0;
        return (
          <li key={group.key}>
            <div>
              <strong>{formatLabel(group.label)}</strong>
              <span>{group.count}</span>
            </div>
            <span className="management-hotspot-bar" aria-hidden="true">
              <span style={{ width: `${percentage}%` }} />
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function GroupList({ groups }: { groups: ManagementDashboardGroup[] }) {
  if (groups.length === 0) {
    return <p className="management-empty">No backlog items.</p>;
  }
  return (
    <ul className="management-group-list">
      {groups.map((group) => (
        <li key={group.key}>
          <span>{formatLabel(group.label)}</span>
          <strong>{group.count}</strong>
        </li>
      ))}
    </ul>
  );
}

function severityClass(value: string | null | undefined): string {
  const normalized = (value || "info").toLowerCase();
  if (normalized === "critical") {
    return "management-severity-critical";
  }
  if (normalized === "warning") {
    return "management-severity-warning";
  }
  return "management-severity-info";
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleDateString();
}

function formatGeneratedAt(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : `Generated ${date.toLocaleString()}`;
}

function formatLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
