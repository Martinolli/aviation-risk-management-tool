import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { getMyDecisionQueue } from "../api/decisionQueue";
import type {
  MyDecisionQueueCommitteeRead,
  MyDecisionQueueRead,
  RiskRecordRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type MyDecisionQueueState =
  | { status: "loading" }
  | { status: "success"; queue: MyDecisionQueueRead }
  | { status: "error"; message: string };

export function MyDecisionQueuePage() {
  const { isAuthenticated, token } = useAuth();
  const [queueState, setQueueState] = useState<MyDecisionQueueState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }
    const tokenToUse = token;

    async function loadDecisionQueue() {
      try {
        const queue = await getMyDecisionQueue(tokenToUse);
        if (isCurrent) {
          setQueueState({ status: "success", queue });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }
        setQueueState({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
      }
    }

    void loadDecisionQueue();
    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated) {
    return <Navigate replace to="/login" />;
  }

  if (!token) {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading decision queue...
      </p>
    );
  }

  return (
    <section
      className="committee-workspace-page"
      aria-labelledby="my-decision-queue-heading"
    >
      <div className="page-header">
        <div>
          <p className="eyebrow">Committee workspace</p>
          <h1 id="my-decision-queue-heading">My Decision Queue</h1>
          <p>
            Review risks currently aligned with your active committee
            memberships.
          </p>
        </div>
      </div>

      {queueState.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading decision queue...
        </p>
      )}

      {queueState.status === "error" && (
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong>Unable to load decision queue.</strong>
          <span>{queueState.message}</span>
        </div>
      )}

      {queueState.status === "success" && (
        <QueueContent queue={queueState.queue} />
      )}
    </section>
  );
}

function QueueContent({ queue }: { queue: MyDecisionQueueRead }) {
  return (
    <>
      <section className="queue-section" aria-labelledby="active-committees-heading">
        <h2 id="active-committees-heading">My active committees</h2>
        {queue.committees.length > 0 ? (
          <div className="committee-card-grid">
            {queue.committees.map((committee) => (
              <article className="committee-card" key={committee.committee_id}>
                <h3>{committee.committee_name}</h3>
                <dl className="committee-card-metadata">
                  <div>
                    <dt>Authority Level</dt>
                    <dd>{formatAuthorityLevel(committee.authority_level)}</dd>
                  </div>
                  <div>
                    <dt>Committee role</dt>
                    <dd>{committee.role_label?.trim() || "Committee Member"}</dd>
                  </div>
                  <div>
                    <dt>Queue scope</dt>
                    <dd>{renderQueueScope(committee)}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        ) : (
          <section className="queue-empty" aria-live="polite">
            <h3>No committee queue</h3>
            <p>
              You are not an active member of any decision committee. No decision
              queue is available for this account.
            </p>
          </section>
        )}
      </section>

      {queue.committees.length > 0 && (
        <section className="queue-section" aria-labelledby="queue-heading">
          <h2 id="queue-heading">Queue</h2>
          {queue.queue_items.length > 0 ? (
            <div className="queue-table-wrapper">
              <table className="queue-table">
                <caption className="visually-hidden">
                  Risks waiting for committee review
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Risk ID</th>
                    <th scope="col">Domain</th>
                    <th scope="col">Workflow status</th>
                    <th scope="col">Committee</th>
                    <th scope="col">Authority Level</th>
                    <th scope="col">Problem description</th>
                    <th scope="col">Updated</th>
                    <th scope="col">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {queue.queue_items.map((item) => {
                    const risk = item.risk_record;
                    return (
                      <tr key={`${item.committee_id}:${risk.id}`}>
                        <td className="risk-id">
                          <Link className="risk-detail-link" to={`/risks/${risk.id}`}>
                            {getRiskDisplayId(risk)}
                          </Link>
                        </td>
                        <td>{formatDomain(risk.domain)}</td>
                        <td>
                          <span className="status-badge">
                            {formatWorkflowStatus(risk.workflow_status)}
                          </span>
                        </td>
                        <td>
                          <span>{item.committee_name}</span>
                          <span className="queue-row-note">
                            {item.role_label?.trim() || "Committee Member"}
                          </span>
                          <span className="queue-row-note">{item.queue_reason}</span>
                        </td>
                        <td>{formatAuthorityLevel(item.authority_level)}</td>
                        <td
                          className="risk-description"
                          title={risk.problem_description}
                        >
                          {risk.problem_description}
                        </td>
                        <td className="muted-text">{getRiskUpdatedDate(risk)}</td>
                        <td>
                          <div className="queue-actions">
                            <Link to={`/risks/${risk.id}`}>View detail</Link>
                            <Link to={`/risks/${risk.id}/decisions/new`}>
                              Record decision
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <section className="queue-empty" aria-live="polite">
              <h3>No decision items</h3>
              <p>No risks are currently waiting for your committee decision.</p>
            </section>
          )}
        </section>
      )}
    </>
  );
}

function renderQueueScope(
  committee: MyDecisionQueueCommitteeRead,
): JSX.Element | string {
  if (!Array.isArray(committee.queue_scope)) {
    return committee.queue_scope;
  }

  return (
    <span className="queue-scope-list">
      {committee.queue_scope.map((domain) => (
        <span key={domain}>{formatDomain(domain)}</span>
      ))}
    </span>
  );
}

function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

function getRiskUpdatedDate(risk: RiskRecordRead): string {
  const date = new Date(risk.updated_at || risk.created_at);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleDateString();
}

function formatAuthorityLevel(level: string): string {
  return level || "Unknown";
}

function formatDomain(domain: string): string {
  return domain || "Unknown";
}

function formatWorkflowStatus(status: string): string {
  return status || "Unknown";
}
