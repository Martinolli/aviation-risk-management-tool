import { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { getMyNotifications } from "../api/notifications";
import type {
  NotificationRead,
  NotificationSeverity,
  NotificationSummaryRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type NotificationsState =
  | { status: "loading" }
  | { status: "success"; summary: NotificationSummaryRead }
  | { status: "error"; message: string };

export function NotificationsPage() {
  const { isAuthenticated, token } = useAuth();
  const [includeInfo, setIncludeInfo] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [notificationsState, setNotificationsState] =
    useState<NotificationsState>({
      status: "loading",
    });

  const refresh = useCallback(() => {
    setRefreshKey((current) => current + 1);
  }, []);

  useEffect(() => {
    let isCurrent = true;
    if (!token) {
      return;
    }
    const tokenToUse = token;

    async function loadNotifications() {
      setNotificationsState({ status: "loading" });
      try {
        const summary = await getMyNotifications(tokenToUse, {
          includeInfo,
          limit: 50,
        });
        if (isCurrent) {
          setNotificationsState({ status: "success", summary });
        }
      } catch (error) {
        if (isCurrent) {
          setNotificationsState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadNotifications();
    return () => {
      isCurrent = false;
    };
  }, [includeInfo, refreshKey, token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  const summary =
    notificationsState.status === "success" ? notificationsState.summary : null;

  return (
    <section className="notifications-page" aria-labelledby="notifications-heading">
      <header className="page-header">
        <div>
          <p className="eyebrow">Needs Attention</p>
          <h1 id="notifications-heading">Notifications</h1>
          <p>
            Review items that need your attention across actions, monitoring,
            committee review, and meeting minutes.
          </p>
        </div>
      </header>

      {summary && <NotificationSummaryCards summary={summary} />}

      <div className="notification-controls">
        <label>
          <input
            checked={includeInfo}
            onChange={(event) => setIncludeInfo(event.target.checked)}
            type="checkbox"
          />
          Include informational notifications
        </label>
        <button onClick={refresh} type="button">
          Refresh
        </button>
      </div>

      {notificationsState.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading Notifications...
        </p>
      )}

      {notificationsState.status === "error" && (
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong>Unable to load Notifications.</strong>
          <span>{notificationsState.message}</span>
        </div>
      )}

      {summary && summary.items.length === 0 && (
        <p className="workspace-status">No notifications requiring attention.</p>
      )}

      {summary && summary.items.length > 0 && (
        <div className="notification-list">
          {summary.items.map((notification) => (
            <NotificationCard
              key={notification.id}
              notification={notification}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function NotificationSummaryCards({
  summary,
}: {
  summary: NotificationSummaryRead;
}) {
  const cards = [
    ["Total", summary.total_count],
    ["Critical", summary.critical_count],
    ["Warning", summary.warning_count],
    ["Info", summary.info_count],
    ["Actions", summary.action_count],
    ["Monitoring", summary.monitoring_count],
    ["Committee review", summary.decision_queue_count],
    ["Meetings", summary.meeting_count],
  ] as const;

  return (
    <section
      aria-label="Notification summary"
      className="notification-summary-grid"
    >
      {cards.map(([label, value]) => (
        <article className="notification-summary-card" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </article>
      ))}
    </section>
  );
}

function NotificationCard({
  notification,
}: {
  notification: NotificationRead;
}) {
  return (
    <article
      className={`notification-card ${notification.severity.toLowerCase()}`}
    >
      <div className="notification-card-header">
        <div>
          <span
            className={`notification-badge ${notification.severity.toLowerCase()}`}
          >
            {formatSeverity(notification.severity)}
          </span>
          <span className="notification-category">
            {formatLabel(notification.category)}
          </span>
        </div>
        <div className="notification-actions">
          {notification.action_url && (
            <Link className="button secondary" to={notification.action_url}>
              Open
            </Link>
          )}
        </div>
      </div>
      <h2>{notification.title}</h2>
      <p>{notification.message}</p>
      <dl className="notification-meta">
        {notification.risk_id && (
          <div>
            <dt>Risk ID</dt>
            <dd>{notification.risk_id}</dd>
          </div>
        )}
        {notification.committee_name && (
          <div>
            <dt>Committee</dt>
            <dd>{notification.committee_name}</dd>
          </div>
        )}
        {notification.due_date && (
          <div>
            <dt>Due date</dt>
            <dd>{notification.due_date}</dd>
          </div>
        )}
      </dl>
    </article>
  );
}

function formatSeverity(value: NotificationSeverity): string {
  return value === "INFO" ? "Info" : formatLabel(value);
}

function formatLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
