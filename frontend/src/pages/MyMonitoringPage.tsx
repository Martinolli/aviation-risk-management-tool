import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { listMyMonitoringReviews } from "../api/riskMonitoring";
import type { RiskMonitoringReviewRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type MyMonitoringState =
  | { status: "loading" }
  | { status: "success"; reviews: RiskMonitoringReviewRead[] }
  | { status: "error"; message: string };

export function MyMonitoringPage() {
  const { isAuthenticated, token } = useAuth();
  const [includeClosed, setIncludeClosed] = useState(false);
  const [monitoringState, setMonitoringState] = useState<MyMonitoringState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadMonitoringReviews() {
      setMonitoringState({ status: "loading" });
      try {
        const reviews = await listMyMonitoringReviews(tokenToUse, {
          includeClosed,
        });
        if (isCurrent) {
          setMonitoringState({ status: "success", reviews });
        }
      } catch (error) {
        if (isCurrent) {
          setMonitoringState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadMonitoringReviews();

    return () => {
      isCurrent = false;
    };
  }, [includeClosed, token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  const reviews =
    monitoringState.status === "success" ? monitoringState.reviews : [];
  const overdueCount = countStatus(reviews, "OVERDUE");
  const dueCount = countStatus(reviews, "DUE");
  const activeCount = countStatus(reviews, "ACTIVE");
  const closedCount = reviews.filter((review) =>
    ["CLOSED", "CANCELLED"].includes(review.status),
  ).length;

  return (
    <section className="monitoring-page" aria-labelledby="my-monitoring-heading">
      <header className="page-header">
        <div>
          <p className="eyebrow">Review cycle</p>
          <h1 id="my-monitoring-heading">My Monitoring</h1>
          <p>
            Track monitoring reviews assigned to you or visible through your
            authorized risk access.
          </p>
        </div>
      </header>

      <section
        aria-label="Monitoring review counts"
        className="monitoring-kpi-grid"
      >
        <article className="monitoring-card overdue">
          <span>Overdue</span>
          <strong>{overdueCount}</strong>
        </article>
        <article className="monitoring-card due">
          <span>Due today</span>
          <strong>{dueCount}</strong>
        </article>
        <article className="monitoring-card active">
          <span>Active</span>
          <strong>{activeCount}</strong>
        </article>
        {includeClosed && (
          <article className="monitoring-card closed">
            <span>Closed</span>
            <strong>{closedCount}</strong>
          </article>
        )}
      </section>

      <div className="monitoring-filter-bar">
        <label>
          <input
            checked={includeClosed}
            onChange={(event) => setIncludeClosed(event.target.checked)}
            type="checkbox"
          />
          Include closed monitoring reviews
        </label>
      </div>

      {monitoringState.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading My Monitoring...
        </p>
      )}

      {monitoringState.status === "error" && (
        <div className="workspace-alert" role="alert">
          <strong>Unable to load My Monitoring.</strong>
          <span>{monitoringState.message}</span>
        </div>
      )}

      {monitoringState.status === "success" && reviews.length === 0 && (
        <p className="monitoring-empty">
          {includeClosed
            ? "No monitoring reviews are available."
            : "No active monitoring reviews."}
        </p>
      )}

      {monitoringState.status === "success" && reviews.length > 0 && (
        <div className="monitoring-table-wrapper">
          <table className="monitoring-queue-table">
            <caption className="visually-hidden">
              Monitoring reviews visible to the current user
            </caption>
            <thead>
              <tr>
                <th scope="col">Status</th>
                <th scope="col">Risk</th>
                <th scope="col">Monitoring Owner</th>
                <th scope="col">Review Frequency</th>
                <th scope="col">Next Review Date</th>
                <th scope="col">Last Reviewed At</th>
                <th scope="col">Review details</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {reviews.map((review) => (
                <tr key={review.id}>
                  <td>
                    <MonitoringStatusBadge status={review.status} />
                  </td>
                  <td>
                    <Link to={`/risks/${review.risk_record_id}`}>
                      {review.risk_record_id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>{review.monitoring_owner_user_id || "Not assigned"}</td>
                  <td>{review.review_frequency || "Not specified"}</td>
                  <td>{review.next_review_date || "Not scheduled"}</td>
                  <td>{formatDateTime(review.last_reviewed_at)}</td>
                  <td>
                    <div className="monitoring-review-excerpt">
                      <span>
                        Outcome: {formatLabel(review.review_outcome) || "Not recorded"}
                      </span>
                      {review.effectiveness_review && (
                        <span>
                          Effectiveness Review: {excerpt(review.effectiveness_review)}
                        </span>
                      )}
                      {review.review_notes && (
                        <span>Review Notes: {excerpt(review.review_notes)}</span>
                      )}
                    </div>
                  </td>
                  <td>
                    <Link
                      className="secondary-link"
                      to={`/risks/${review.risk_record_id}`}
                    >
                      {isOpenReview(review)
                        ? "Open review cycle"
                        : "Open risk detail"}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function MonitoringStatusBadge({ status }: { status: string }) {
  return (
    <span className={`monitoring-status-badge ${status.toLowerCase()}`}>
      {formatLabel(status)}
    </span>
  );
}

function countStatus(
  reviews: RiskMonitoringReviewRead[],
  status: string,
): number {
  return reviews.filter((review) => review.status === status).length;
}

function isOpenReview(review: RiskMonitoringReviewRead): boolean {
  return ["ACTIVE", "DUE", "OVERDUE"].includes(review.status);
}

function excerpt(value: string, limit = 100): string {
  const normalized = value.trim();
  return normalized.length > limit
    ? `${normalized.slice(0, limit).trimEnd()}…`
    : normalized;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not reviewed";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not reviewed" : date.toLocaleString();
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
