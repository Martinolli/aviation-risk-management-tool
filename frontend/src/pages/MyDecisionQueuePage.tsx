import { useEffect, useMemo, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { listCommitteeMembers } from "../api/committeeMembers";
import { listCommittees } from "../api/committees";
import { listRisks } from "../api/risks";
import type {
  CommitteeMemberRead,
  CommitteeRead,
  RiskRecordRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type MyDecisionQueueState =
  | { status: "loading" }
  | {
      status: "success";
      risks: RiskRecordRead[];
      committees: CommitteeRead[];
      memberships: CommitteeMemberRead[];
    }
  | { status: "error"; message: string };

interface QueueItem {
  risk: RiskRecordRead;
  committee: CommitteeRead;
  membership: CommitteeMemberRead | undefined;
}

const LOW_QUEUE_STATUSES = new Set([
  "SUBMITTED_TO_OPERATIONAL_BOARD",
  "UNDER_OPERATIONAL_BOARD_REVIEW",
]);

const MIDDLE_QUEUE_STATUSES = new Set([
  "ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE",
  "UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW",
]);

const HIGH_QUEUE_STATUSES = new Set([
  "ESCALATED_TO_EXECUTIVE_COMMITTEE",
  "UNDER_EXECUTIVE_COMMITTEE_REVIEW",
]);

const ALL_DOMAINS = [
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

export function MyDecisionQueuePage() {
  const { isAuthenticated, token, user } = useAuth();
  const [queueState, setQueueState] = useState<MyDecisionQueueState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token || !user?.id) {
      return;
    }

    const tokenToUse = token;
    const currentUserId = user.id;

    async function loadDecisionQueue() {
      try {
        const [risks, committees, memberships] = await Promise.all([
          listRisks(tokenToUse),
          listCommittees(tokenToUse),
          listCommitteeMembers(tokenToUse, { userId: currentUserId }),
        ]);

        if (isCurrent) {
          setQueueState({ status: "success", risks, committees, memberships });
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
  }, [token, user?.id]);

  const queueContext = useMemo(() => {
    if (queueState.status !== "success") {
      return null;
    }

    const activeMemberships = getActiveMemberships(queueState.memberships);
    const userCommittees = getUserCommittees(
      queueState.committees,
      activeMemberships,
    );
    const queueItems = buildQueueItems(
      queueState.risks,
      userCommittees,
      activeMemberships,
    );

    return { activeMemberships, userCommittees, queueItems };
  }, [queueState]);

  if (!isAuthenticated) {
    return <Navigate replace to="/login" />;
  }

  if (!token || !user?.id) {
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

      {queueState.status === "success" && queueContext && (
        <>
          <section
            className="queue-section"
            aria-labelledby="active-committees-heading"
          >
            <h2 id="active-committees-heading">My active committees</h2>
            {queueContext.userCommittees.length > 0 ? (
              <div className="committee-card-grid">
                {queueContext.userCommittees.map((committee) => {
                  const membership = findMembershipForCommittee(
                    queueContext.activeMemberships,
                    committee.id,
                  );

                  return (
                    <article className="committee-card" key={committee.id}>
                      <h3>{committee.name}</h3>
                      <dl className="committee-card-metadata">
                        <div>
                          <dt>Authority Level</dt>
                          <dd>{formatAuthorityLevel(committee.authority_level)}</dd>
                        </div>
                        <div>
                          <dt>Committee role</dt>
                          <dd>{membership?.role_label?.trim() || "Committee Member"}</dd>
                        </div>
                        <div>
                          <dt>Queue scope</dt>
                          <dd>{getQueueScope(committee)}</dd>
                        </div>
                      </dl>
                    </article>
                  );
                })}
              </div>
            ) : (
              <section className="queue-empty" aria-live="polite">
                <h3>No committee queue</h3>
                <p>
                  You are not an active member of any decision committee. No
                  decision queue is available for this account.
                </p>
              </section>
            )}
          </section>

          {queueContext.userCommittees.length > 0 && (
            <section className="queue-section" aria-labelledby="queue-heading">
              <h2 id="queue-heading">Queue</h2>
              {queueContext.queueItems.length > 0 ? (
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
                      {queueContext.queueItems.map(
                        ({ risk, committee, membership }) => (
                          <tr key={`${committee.id}:${risk.id}`}>
                            <td className="risk-id">
                              <Link
                                className="risk-detail-link"
                                to={`/risks/${risk.id}`}
                              >
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
                              <span>{committee.name}</span>
                              {membership?.role_label?.trim() && (
                                <span className="queue-row-note">
                                  {membership.role_label}
                                </span>
                              )}
                            </td>
                            <td>{formatAuthorityLevel(committee.authority_level)}</td>
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
                        ),
                      )}
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
      )}
    </section>
  );
}

export function getActiveMemberships(
  memberships: CommitteeMemberRead[],
): CommitteeMemberRead[] {
  return memberships.filter((membership) => membership.is_active);
}

export function getUserCommittees(
  committees: CommitteeRead[],
  memberships: CommitteeMemberRead[],
): CommitteeRead[] {
  const activeCommitteeIds = new Set(
    getActiveMemberships(memberships).map((membership) => membership.committee_id),
  );

  return committees.filter((committee) => activeCommitteeIds.has(committee.id));
}

export function getDomainsForCommittee(committee: CommitteeRead): string[] {
  switch (committee.name) {
    case "Aircraft Safety Committee - Engineering Board":
      return ["ENGINEERING", "CONTINUED_AIRWORTHINESS"];
    case "Flight Test Safety Committee - Operation":
      return ["FLIGHT_TEST"];
    case "Industrial Safety Committee - Quality, Manufacturing, Production, Supply Chain, OHSE":
      return [
        "QUALITY",
        "MANUFACTURING",
        "PRODUCTION",
        "SUPPLY_CHAIN",
        "OHSE",
        "MAINTENANCE",
        "SUPPLIER_INTERFACE",
      ];
    case "Risk Management Committee":
    case "Executive Safety Management Committee":
      return ALL_DOMAINS;
    default:
      return [];
  }
}

export function isRiskInCommitteeQueue(
  risk: RiskRecordRead,
  committee: CommitteeRead,
): boolean {
  if (committee.authority_level === "LOW") {
    return (
      LOW_QUEUE_STATUSES.has(risk.workflow_status) &&
      risk.board_of_origin_id === committee.id
    );
  }

  if (committee.authority_level === "MIDDLE") {
    return MIDDLE_QUEUE_STATUSES.has(risk.workflow_status);
  }

  if (committee.authority_level === "HIGH") {
    return HIGH_QUEUE_STATUSES.has(risk.workflow_status);
  }

  return false;
}

function buildQueueItems(
  risks: RiskRecordRead[],
  committees: CommitteeRead[],
  memberships: CommitteeMemberRead[],
): QueueItem[] {
  const dedupedItems = new Map<string, QueueItem>();

  committees.forEach((committee) => {
    risks
      .filter((risk) => isRiskInCommitteeQueue(risk, committee))
      .forEach((risk) => {
        const key = `${committee.id}:${risk.id}`;

        if (!dedupedItems.has(key)) {
          dedupedItems.set(key, {
            risk,
            committee,
            membership: findMembershipForCommittee(memberships, committee.id),
          });
        }
      });
  });

  return Array.from(dedupedItems.values()).sort(
    (first, second) =>
      getRiskTime(second.risk) - getRiskTime(first.risk) ||
      first.committee.name.localeCompare(second.committee.name),
  );
}

function findMembershipForCommittee(
  memberships: CommitteeMemberRead[],
  committeeId: string,
): CommitteeMemberRead | undefined {
  return memberships.find(
    (membership) => membership.is_active && membership.committee_id === committeeId,
  );
}

function getQueueScope(committee: CommitteeRead): JSX.Element | string {
  if (committee.authority_level === "MIDDLE") {
    return "Escalated RMC risks";
  }

  if (committee.authority_level === "HIGH") {
    return "Escalated executive risks";
  }

  const domains = getDomainsForCommittee(committee);

  if (domains.length === 0) {
    return "No mapped domains yet.";
  }

  return (
    <span className="queue-scope-list">
      {domains.map((domain) => (
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

function getRiskTime(risk: RiskRecordRead): number {
  const date = new Date(risk.updated_at || risk.created_at);

  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
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
