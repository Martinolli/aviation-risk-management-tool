import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { listMyMonitoringReviews } from "../api/riskMonitoring";
import { listRisks } from "../api/risks";
import type { RiskMonitoringReviewRead, RiskRecordRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import {
  getRiskPackageStatusLabel,
  getRiskPackageStatusTone,
} from "../utils/riskReadiness";

type DashboardState =
  | { status: "loading" }
  | {
      status: "success";
      risks: RiskRecordRead[];
      monitoringReviews: RiskMonitoringReviewRead[];
      monitoringUnavailable: boolean;
    }
  | { status: "error"; message: string };

interface DistributionGroup {
  key: string;
  label: string;
  count: number;
  percentage: number;
}

interface AttentionItem {
  risk: RiskRecordRead;
  reason: string;
  priority: number;
}

const WORKFLOW_STATUS_ORDER = [
  "DRAFT",
  "SUBMITTED_TO_OPERATIONAL_BOARD",
  "UNDER_OPERATIONAL_BOARD_REVIEW",
  "APPROVED_AT_OPERATIONAL_BOARD",
  "ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE",
  "ESCALATED_TO_RMC",
  "UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW",
  "UNDER_RMC_REVIEW",
  "APPROVED_AT_RISK_MANAGEMENT_COMMITTEE",
  "ESCALATED_TO_EXECUTIVE_COMMITTEE",
  "ESCALATED_TO_EXECUTIVE",
  "UNDER_EXECUTIVE_COMMITTEE_REVIEW",
  "UNDER_EXECUTIVE_REVIEW",
  "RETURNED_FOR_REVISION",
  "ACCEPTED",
  "REJECTED",
  "CLOSED",
] as const;

const FINAL_OR_DRAFT_STATUSES = new Set([
  "DRAFT",
  "CLOSED",
  "ACCEPTED",
  "REJECTED",
]);

export function RiskDashboardPage() {
  const { isAuthenticated, token } = useAuth();
  const [dashboardState, setDashboardState] = useState<DashboardState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadDashboard() {
      const [riskResult, monitoringResult] = await Promise.allSettled([
        listRisks(tokenToUse),
        listMyMonitoringReviews(tokenToUse, { includeClosed: true }),
      ]);

      if (riskResult.status === "rejected") {
        if (isCurrent) {
          setDashboardState({
            status: "error",
            message:
              riskResult.reason instanceof ApiError
                ? riskResult.reason.message
                : "Please try again shortly.",
          });
        }
        return;
      }

      if (isCurrent) {
        setDashboardState({
          status: "success",
          risks: riskResult.value,
          monitoringReviews:
            monitoringResult.status === "fulfilled" ? monitoringResult.value : [],
          monitoringUnavailable: monitoringResult.status === "rejected",
        });
      }
    }

    void loadDashboard();

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
        Loading risk dashboard...
      </p>
    );
  }

  if (dashboardState.status === "error") {
    return (
      <section className="dashboard-page" aria-labelledby="dashboard-load-error">
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="dashboard-load-error">Unable to load risk dashboard.</strong>
          <span>{dashboardState.message}</span>
        </div>
      </section>
    );
  }

  const risks = dashboardState.risks;
  const monitoringReviews = dashboardState.monitoringReviews;
  const priorityMonitoringReviews = monitoringReviews
    .filter((review) => ["OVERDUE", "DUE"].includes(review.status))
    .slice(0, 5);
  const draftRisks = risks.filter(isDraftRisk);
  const packageReadyDrafts = draftRisks.filter(isPackageMinimumComplete);
  const incompleteDraftCount = draftRisks.length - packageReadyDrafts.length;
  const workflowGroups = getStatusGroups(risks);
  const domainGroups = getDomainGroups(risks);
  const recentRisks = getRecentRisks(risks, 5);
  const attentionItems = getAttentionItems(risks, 5);
  const kpis = [
    {
      label: "Total risks",
      value: risks.length,
      detail: "Authorized risk records",
    },
    {
      label: "Open risks",
      value: risks.filter(isOpenRisk).length,
      detail: "Lifecycle status is not CLOSED",
    },
    {
      label: "Closed risks",
      value: risks.filter(isClosedRisk).length,
      detail: "Closed workflow or lifecycle status",
    },
    {
      label: "Draft risks",
      value: draftRisks.length,
      detail: "Workflow status: DRAFT",
    },
    {
      label: "In workflow",
      value: risks.filter(isInWorkflowRisk).length,
      detail: "Submitted, review, or escalation",
    },
    {
      label: "Package-ready drafts",
      value: packageReadyDrafts.length,
      detail: "Board of Origin and minimum package complete",
    },
    {
      label: "Monitoring risks",
      value: risks.filter((risk) => risk.lifecycle_status === "MONITORING").length,
      detail: "Lifecycle status: MONITORING",
    },
  ];

  return (
    <section className="dashboard-page" aria-labelledby="risk-dashboard-heading">
      <header className="page-header">
        <div>
          <p className="eyebrow">SMS overview</p>
          <h1 id="risk-dashboard-heading">Risk dashboard</h1>
          <p>
            Monitor authorized risk records, workflow distribution, package
            readiness, and recent activity.
          </p>
        </div>
        <Link className="button" to="/risks">
          View risk records
        </Link>
      </header>

      <section className="dashboard-grid" aria-label="Risk key performance indicators">
        {kpis.map((kpi) => (
          <article className="dashboard-card dashboard-kpi" key={kpi.label}>
            <span>{kpi.label}</span>
            <strong>{kpi.value}</strong>
            <small>{kpi.detail}</small>
          </article>
        ))}
      </section>

      <section
        className="dashboard-section monitoring-dashboard-snapshot"
        aria-labelledby="monitoring-dashboard-heading"
      >
        <div className="dashboard-section-header">
          <div>
            <p className="eyebrow">Review cycle</p>
            <h2 id="monitoring-dashboard-heading">Monitoring review snapshot</h2>
          </div>
          <Link className="secondary-link" to="/my-monitoring">
            View My Monitoring
          </Link>
        </div>

        {dashboardState.monitoringUnavailable ? (
          <p className="monitoring-snapshot-warning" role="status">
            Monitoring snapshot unavailable.
          </p>
        ) : (
          <>
            <div className="monitoring-kpi-grid dashboard-monitoring-kpis">
              <article className="monitoring-card overdue">
                <span>Overdue reviews</span>
                <strong>{countMonitoringStatus(monitoringReviews, "OVERDUE")}</strong>
              </article>
              <article className="monitoring-card due">
                <span>Due today</span>
                <strong>{countMonitoringStatus(monitoringReviews, "DUE")}</strong>
              </article>
              <article className="monitoring-card active">
                <span>Active reviews</span>
                <strong>{countMonitoringStatus(monitoringReviews, "ACTIVE")}</strong>
              </article>
              <article className="monitoring-card closed">
                <span>Closed reviews</span>
                <strong>
                  {
                    monitoringReviews.filter((review) =>
                      ["CLOSED", "CANCELLED"].includes(review.status),
                    ).length
                  }
                </strong>
              </article>
            </div>

            {priorityMonitoringReviews.length === 0 ? (
              <p className="monitoring-empty">
                No overdue or due monitoring reviews.
              </p>
            ) : (
              <ul className="monitoring-dashboard-list">
                {priorityMonitoringReviews.map((review) => (
                  <li key={review.id}>
                    <span
                      className={`monitoring-status-badge ${review.status.toLowerCase()}`}
                    >
                      {formatLabel(review.status)}
                    </span>
                    <Link to={`/risks/${review.risk_record_id}`}>
                      Risk {review.risk_record_id.slice(0, 8)}
                    </Link>
                    <span>
                      Next Review Date: {review.next_review_date || "Not scheduled"}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <div className="dashboard-section-grid">
        <section
          className="dashboard-section"
          aria-labelledby="workflow-distribution-heading"
        >
          <div className="dashboard-section-header">
            <div>
              <p className="eyebrow">Workflow status</p>
              <h2 id="workflow-distribution-heading">Workflow distribution</h2>
            </div>
            <span>{risks.length} total</span>
          </div>
          {workflowGroups.length === 0 ? (
            <p className="dashboard-empty">No workflow data available.</p>
          ) : (
            <ul className="dashboard-distribution-list">
              {workflowGroups.map((group) => (
                <li className="dashboard-distribution-item" key={group.key}>
                  <div>
                    <strong>{group.label}</strong>
                    <span>
                      {group.count} · {group.percentage}%
                    </span>
                  </div>
                  <svg
                    aria-label={`${group.label}: ${group.percentage}%`}
                    className="dashboard-bar"
                    preserveAspectRatio="none"
                    role="img"
                    viewBox="0 0 100 8"
                  >
                    <rect
                      className="dashboard-bar-track"
                      height="8"
                      rx="4"
                      width="100"
                    />
                    <rect
                      className="dashboard-bar-fill"
                      height="8"
                      rx="4"
                      width={group.percentage}
                    />
                  </svg>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section
          className="dashboard-section"
          aria-labelledby="domain-distribution-heading"
        >
          <div className="dashboard-section-header">
            <div>
              <p className="eyebrow">Risk domains</p>
              <h2 id="domain-distribution-heading">Domain distribution</h2>
            </div>
            <span>{domainGroups.length} domains</span>
          </div>
          {domainGroups.length === 0 ? (
            <p className="dashboard-empty">No domain data available.</p>
          ) : (
            <ul className="dashboard-distribution-list">
              {domainGroups.map((group) => (
                <li className="dashboard-distribution-item" key={group.key}>
                  <div>
                    <strong>{group.label}</strong>
                    <span>
                      {group.count} · {group.percentage}%
                    </span>
                  </div>
                  <svg
                    aria-label={`${group.label}: ${group.percentage}%`}
                    className="dashboard-bar"
                    preserveAspectRatio="none"
                    role="img"
                    viewBox="0 0 100 8"
                  >
                    <rect
                      className="dashboard-bar-track"
                      height="8"
                      rx="4"
                      width="100"
                    />
                    <rect
                      className="dashboard-bar-fill domain"
                      height="8"
                      rx="4"
                      width={group.percentage}
                    />
                  </svg>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section
        className="dashboard-section"
        aria-labelledby="draft-readiness-heading"
      >
        <div className="dashboard-section-header">
          <div>
            <p className="eyebrow">Package readiness</p>
            <h2 id="draft-readiness-heading">Draft readiness snapshot</h2>
          </div>
          <span>{draftRisks.length} drafts</span>
        </div>
        <div className="dashboard-readiness-grid">
          <article className="dashboard-readiness-item warning">
            <strong>{incompleteDraftCount}</strong>
            <span>Draft incomplete</span>
            <small>Missing Board of Origin or minimum package fields.</small>
          </article>
          <article className="dashboard-readiness-item info">
            <strong>{packageReadyDrafts.length}</strong>
            <span>Package complete</span>
            <small>Minimum package fields and Board of Origin are recorded.</small>
          </article>
        </div>
        <p className="dashboard-guidance">
          Initial assessment readiness is confirmed on the Risk Detail and
          Submit pages.
        </p>
      </section>

      <section
        className="dashboard-section"
        aria-labelledby="recent-activity-heading"
      >
        <div className="dashboard-section-header">
          <div>
            <p className="eyebrow">Latest updates</p>
            <h2 id="recent-activity-heading">Recent activity</h2>
          </div>
        </div>
        {recentRisks.length === 0 ? (
          <p className="dashboard-empty">No recent risk activity.</p>
        ) : (
          <div className="dashboard-table-wrapper recent-risk-list">
            <table className="dashboard-table">
              <caption className="visually-hidden">
                Most recently updated authorized risks
              </caption>
              <thead>
                <tr>
                  <th scope="col">Risk ID</th>
                  <th scope="col">Problem description</th>
                  <th scope="col">Domain</th>
                  <th scope="col">Workflow status</th>
                  <th scope="col">Readiness</th>
                  <th scope="col">Updated</th>
                </tr>
              </thead>
              <tbody>
                {recentRisks.map((risk) => {
                  const readinessLabel = getRiskPackageStatusLabel(risk);
                  const readinessTone = getRiskPackageStatusTone(risk);

                  return (
                    <tr key={risk.id}>
                      <td>
                        <Link to={`/risks/${risk.id}`}>
                          {getRiskDisplayId(risk)}
                        </Link>
                      </td>
                      <td className="dashboard-risk-description">
                        {risk.problem_description}
                      </td>
                      <td>{formatLabel(risk.domain)}</td>
                      <td>{getWorkflowStatusLabel(risk.workflow_status)}</td>
                      <td>
                        <span className={`readiness-badge ${readinessTone}`}>
                          {readinessLabel}
                        </span>
                      </td>
                      <td>{formatDate(risk.updated_at || risk.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section
        className="dashboard-section"
        aria-labelledby="attention-items-heading"
      >
        <div className="dashboard-section-header">
          <div>
            <p className="eyebrow">Operational hints</p>
            <h2 id="attention-items-heading">Needs attention</h2>
          </div>
          <span>Not a replacement for My Decision Queue</span>
        </div>
        {attentionItems.length === 0 ? (
          <p className="dashboard-empty">No immediate attention items.</p>
        ) : (
          <ul className="attention-list">
            {attentionItems.map(({ risk, reason }) => (
              <li className="attention-item" key={risk.id}>
                <div>
                  <Link to={`/risks/${risk.id}`}>{getRiskDisplayId(risk)}</Link>
                  <strong>{reason}</strong>
                  <p>{risk.problem_description}</p>
                </div>
                <Link className="secondary-link" to={`/risks/${risk.id}`}>
                  Open risk detail
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}

function isClosedRisk(risk: RiskRecordRead): boolean {
  return risk.lifecycle_status === "CLOSED" || risk.workflow_status === "CLOSED";
}

function isOpenRisk(risk: RiskRecordRead): boolean {
  return risk.lifecycle_status !== "CLOSED";
}

function isDraftRisk(risk: RiskRecordRead): boolean {
  return risk.workflow_status === "DRAFT";
}

function isInWorkflowRisk(risk: RiskRecordRead): boolean {
  return !FINAL_OR_DRAFT_STATUSES.has(risk.workflow_status);
}

function isPackageMinimumComplete(risk: RiskRecordRead): boolean {
  return Boolean(
    risk.board_of_origin_id &&
      risk.system_scope?.trim() &&
      risk.central_event?.trim() &&
      risk.hazard_statement?.trim(),
  );
}

function getWorkflowStatusLabel(status: string): string {
  return formatLabel(status);
}

function getStatusGroups(risks: RiskRecordRead[]): DistributionGroup[] {
  const counts = new Map<string, number>();
  risks.forEach((risk) => {
    counts.set(risk.workflow_status, (counts.get(risk.workflow_status) ?? 0) + 1);
  });

  return Array.from(counts, ([key, count]) => ({
    key,
    label: getWorkflowStatusLabel(key),
    count,
    percentage: getPercentage(count, risks.length),
  })).sort(compareWorkflowGroups);
}

function getDomainGroups(risks: RiskRecordRead[]): DistributionGroup[] {
  const counts = new Map<string, number>();
  risks.forEach((risk) => {
    counts.set(risk.domain, (counts.get(risk.domain) ?? 0) + 1);
  });

  return Array.from(counts, ([key, count]) => ({
    key,
    label: formatLabel(key),
    count,
    percentage: getPercentage(count, risks.length),
  })).sort(
    (first, second) =>
      second.count - first.count || first.label.localeCompare(second.label),
  );
}

function getPercentage(count: number, total: number): number {
  return total > 0 ? Math.round((count / total) * 100) : 0;
}

function countMonitoringStatus(
  reviews: RiskMonitoringReviewRead[],
  status: string,
): number {
  return reviews.filter((review) => review.status === status).length;
}

function getRecentRisks(risks: RiskRecordRead[], limit: number): RiskRecordRead[] {
  return [...risks]
    .sort((first, second) => getRiskTimestamp(second) - getRiskTimestamp(first))
    .slice(0, limit);
}

function getAttentionItems(
  risks: RiskRecordRead[],
  limit: number,
): AttentionItem[] {
  const items = risks.flatMap<AttentionItem>((risk) => {
    if (isDraftRisk(risk) && !isPackageMinimumComplete(risk)) {
      return [{ risk, reason: "Complete risk package", priority: 1 }];
    }
    if (isDraftRisk(risk)) {
      return [
        {
          risk,
          reason: "Add initial assessment / confirm submission readiness",
          priority: 2,
        },
      ];
    }
    if (risk.workflow_status === "RETURNED_FOR_REVISION") {
      return [{ risk, reason: "Returned for revision", priority: 3 }];
    }
    if (isInWorkflowRisk(risk)) {
      return [{ risk, reason: "Committee review in progress", priority: 4 }];
    }
    return [];
  });

  return items
    .sort(
      (first, second) =>
        first.priority - second.priority ||
        getRiskTimestamp(second.risk) - getRiskTimestamp(first.risk),
    )
    .slice(0, limit);
}

function compareWorkflowGroups(
  first: DistributionGroup,
  second: DistributionGroup,
): number {
  const firstIndex = WORKFLOW_STATUS_ORDER.indexOf(
    first.key as (typeof WORKFLOW_STATUS_ORDER)[number],
  );
  const secondIndex = WORKFLOW_STATUS_ORDER.indexOf(
    second.key as (typeof WORKFLOW_STATUS_ORDER)[number],
  );
  const normalizedFirst = firstIndex === -1 ? Number.MAX_SAFE_INTEGER : firstIndex;
  const normalizedSecond = secondIndex === -1 ? Number.MAX_SAFE_INTEGER : secondIndex;
  return normalizedFirst - normalizedSecond || first.label.localeCompare(second.label);
}

function getRiskTimestamp(risk: RiskRecordRead): number {
  const updatedAt = Date.parse(risk.updated_at);
  if (!Number.isNaN(updatedAt)) {
    return updatedAt;
  }
  const createdAt = Date.parse(risk.created_at);
  return Number.isNaN(createdAt) ? 0 : createdAt;
}

function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString();
}

function formatLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
