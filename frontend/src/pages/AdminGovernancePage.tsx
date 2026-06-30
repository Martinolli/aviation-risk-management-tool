import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { listCommitteeMembers } from "../api/committeeMembers";
import { listCommittees } from "../api/committees";
import type {
  CommitteeMemberRead,
  CommitteeRead,
  UserRead,
} from "../api/types";
import { listUsers } from "../api/users";
import { useAuth } from "../auth/AuthContext";

type GovernanceDataState =
  | { status: "loading" }
  | {
      status: "success";
      users: UserRead[];
      committees: CommitteeRead[];
      memberships: CommitteeMemberRead[];
    }
  | { status: "error"; message: string };

const AUTHORITY_LEVEL_ORDER: Record<string, number> = {
  LOW: 0,
  MIDDLE: 1,
  HIGH: 2,
};

export function AdminGovernancePage() {
  const { isAuthenticated, token } = useAuth();
  const [governanceData, setGovernanceData] = useState<GovernanceDataState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadGovernanceData() {
      try {
        const [users, committees, memberships] = await Promise.all([
          listUsers(tokenToUse, { includeInactive: true }),
          listCommittees(tokenToUse, { includeArchived: true }),
          listCommitteeMembers(tokenToUse, { includeInactive: true }),
        ]);

        if (isCurrent) {
          setGovernanceData({
            status: "success",
            users,
            committees,
            memberships,
          });
        }
      } catch (error) {
        if (isCurrent) {
          setGovernanceData({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadGovernanceData();

    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (governanceData.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading governance data...
      </p>
    );
  }

  if (governanceData.status === "error") {
    return (
      <section
        className="admin-governance-page"
        aria-labelledby="governance-load-error"
      >
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="governance-load-error">
            Unable to load governance data.
          </strong>
          <span>{governanceData.message}</span>
        </div>
      </section>
    );
  }

  const { users, committees, memberships } = governanceData;
  const sortedCommittees = [...committees].sort(compareCommittees);
  const sortedUsers = [...users].sort(compareUsers);
  const usersById = new Map(users.map((user) => [user.id, user]));
  const committeesById = new Map(
    committees.map((committee) => [committee.id, committee]),
  );
  const activeUserCount = users.filter((user) => user.is_active).length;
  const activeMembershipCount = memberships.filter(
    (membership) => membership.is_active,
  ).length;

  return (
    <section
      className="admin-governance-page"
      aria-labelledby="admin-governance-heading"
    >
      <header className="page-header">
        <div>
          <p className="eyebrow">Administration</p>
          <h1 id="admin-governance-heading">Governance management</h1>
          <p>
            Review users, committees, Authority Levels, and active committee
            memberships.
          </p>
        </div>
      </header>

      <section className="admin-summary-grid" aria-label="Governance summary">
        <article className="admin-summary-card">
          <h2>Users</h2>
          <strong>{users.length}</strong>
          <span>Total users</span>
          <dl>
            <div>
              <dt>Active</dt>
              <dd>{activeUserCount}</dd>
            </div>
            <div>
              <dt>Inactive</dt>
              <dd>{users.length - activeUserCount}</dd>
            </div>
          </dl>
        </article>

        <article className="admin-summary-card">
          <h2>Committees</h2>
          <strong>{committees.length}</strong>
          <span>Total committees</span>
          <dl>
            {(["LOW", "MIDDLE", "HIGH"] as const).map((authorityLevel) => (
              <div key={authorityLevel}>
                <dt>{authorityLevel}</dt>
                <dd>
                  {
                    committees.filter(
                      (committee) =>
                        committee.authority_level === authorityLevel,
                    ).length
                  }
                </dd>
              </div>
            ))}
          </dl>
        </article>

        <article className="admin-summary-card">
          <h2>Memberships</h2>
          <strong>{memberships.length}</strong>
          <span>Total memberships</span>
          <dl>
            <div>
              <dt>Active</dt>
              <dd>{activeMembershipCount}</dd>
            </div>
            <div>
              <dt>Inactive</dt>
              <dd>{memberships.length - activeMembershipCount}</dd>
            </div>
          </dl>
        </article>
      </section>

      <section
        className="governance-section"
        aria-labelledby="committees-members-heading"
      >
        <div className="governance-section-heading">
          <div>
            <p className="eyebrow">Committee structure</p>
            <h2 id="committees-members-heading">Committees and members</h2>
          </div>
          <span className="governance-read-only">Read only</span>
        </div>

        {sortedCommittees.length === 0 ? (
          <p className="workspace-empty">No committees found.</p>
        ) : (
          <div className="committee-governance-grid">
            {sortedCommittees.map((committee) => {
              const committeeMemberships = memberships
                .filter(
                  (membership) => membership.committee_id === committee.id,
                )
                .sort((first, second) =>
                  compareMemberships(first, second, usersById),
                );

              return (
                <article className="committee-governance-card" key={committee.id}>
                  <div className="committee-governance-header">
                    <h3>{committee.name}</h3>
                    <span
                      className={`governance-chip ${committee.is_active ? "" : "inactive"}`}
                    >
                      {committee.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  <div className="committee-governance-metadata">
                    <span
                      className={`governance-chip ${getAuthorityLevelClass(committee.authority_level)}`}
                    >
                      Authority Level: {committee.authority_level}
                    </span>
                    <span className="governance-chip">
                      {formatLabel(committee.committee_type)}
                    </span>
                    <span className="governance-chip">
                      {committee.is_fixed ? "Fixed / protected" : "Configurable"}
                    </span>
                  </div>

                  <h4>Members</h4>
                  {committeeMemberships.length === 0 ? (
                    <p className="governance-empty">No members assigned.</p>
                  ) : (
                    <ul className="committee-member-list">
                      {committeeMemberships.map((membership) => {
                        const member = usersById.get(membership.user_id);

                        return (
                          <li key={membership.id}>
                            <div className="committee-member-identity">
                              <strong>
                                {member?.display_name || "Unknown user"}
                              </strong>
                              <span>{member?.email || membership.user_id}</span>
                            </div>
                            <div className="committee-member-role">
                              <span>{membership.role_label || "Committee member"}</span>
                              <span
                                className={`governance-chip ${membership.is_active ? "" : "inactive"}`}
                              >
                                {membership.is_active
                                  ? "Active membership"
                                  : "Inactive membership"}
                              </span>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section
        className="governance-section"
        aria-labelledby="users-memberships-heading"
      >
        <div className="governance-section-heading">
          <div>
            <p className="eyebrow">Directory</p>
            <h2 id="users-memberships-heading">Users and memberships</h2>
          </div>
          <span className="governance-read-only">Read only</span>
        </div>

        <div className="user-governance-table-wrapper">
          <table className="user-governance-table">
            <caption className="visually-hidden">
              Users and committee memberships
            </caption>
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Email</th>
                <th scope="col">Status</th>
                <th scope="col">Committee memberships</th>
                <th scope="col">Governance roles</th>
              </tr>
            </thead>
            <tbody>
              {sortedUsers.length === 0 ? (
                <tr>
                  <td className="governance-table-empty" colSpan={5}>
                    No users found.
                  </td>
                </tr>
              ) : (
                sortedUsers.map((user) => {
                  const userMemberships = memberships
                    .filter((membership) => membership.user_id === user.id)
                    .sort((first, second) =>
                      compareUserMemberships(
                        first,
                        second,
                        committeesById,
                      ),
                    );
                  const governanceRoles = Array.from(
                    new Set(
                      userMemberships.map(
                        (membership) =>
                          membership.role_label || "Committee member",
                      ),
                    ),
                  ).sort((first, second) => first.localeCompare(second));

                  return (
                    <tr key={user.id}>
                      <td className="governance-user-name">
                        {user.display_name}
                      </td>
                      <td className="governance-user-email">{user.email}</td>
                      <td>
                        <span
                          className={`governance-chip ${user.is_active ? "" : "inactive"}`}
                        >
                          {user.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td>
                        {userMemberships.length === 0 ? (
                          <span className="governance-empty">
                            No committee membership
                          </span>
                        ) : (
                          <ul className="membership-chip-list">
                            {userMemberships.map((membership) => {
                              const committee = committeesById.get(
                                membership.committee_id,
                              );

                              return (
                                <li
                                  className={`governance-membership-chip ${membership.is_active ? "" : "inactive"}`}
                                  key={membership.id}
                                >
                                  <strong>
                                    {committee?.name || membership.committee_id}
                                  </strong>
                                  <span>
                                    Authority Level: {committee?.authority_level || "Unknown"}
                                  </span>
                                  <span>
                                    {membership.role_label || "Committee member"}
                                    {!membership.is_active && " · Inactive"}
                                  </span>
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </td>
                      <td>
                        {governanceRoles.length === 0 ? (
                          <span className="governance-empty">
                            No governance role
                          </span>
                        ) : (
                          <div className="membership-chip-list">
                            {governanceRoles.map((role) => (
                              <span className="governance-chip" key={role}>
                                {role}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

function compareCommittees(first: CommitteeRead, second: CommitteeRead): number {
  const authorityDifference =
    (AUTHORITY_LEVEL_ORDER[first.authority_level] ?? Number.MAX_SAFE_INTEGER) -
    (AUTHORITY_LEVEL_ORDER[second.authority_level] ?? Number.MAX_SAFE_INTEGER);
  return authorityDifference || first.name.localeCompare(second.name);
}

function compareUsers(first: UserRead, second: UserRead): number {
  if (first.is_active !== second.is_active) {
    return first.is_active ? -1 : 1;
  }
  return first.display_name.localeCompare(second.display_name);
}

function compareMemberships(
  first: CommitteeMemberRead,
  second: CommitteeMemberRead,
  usersById: Map<string, UserRead>,
): number {
  if (first.is_active !== second.is_active) {
    return first.is_active ? -1 : 1;
  }
  const roleDifference = (first.role_label || "").localeCompare(
    second.role_label || "",
  );
  if (roleDifference) {
    return roleDifference;
  }
  return (usersById.get(first.user_id)?.display_name || first.user_id).localeCompare(
    usersById.get(second.user_id)?.display_name || second.user_id,
  );
}

function compareUserMemberships(
  first: CommitteeMemberRead,
  second: CommitteeMemberRead,
  committeesById: Map<string, CommitteeRead>,
): number {
  if (first.is_active !== second.is_active) {
    return first.is_active ? -1 : 1;
  }
  const firstCommittee = committeesById.get(first.committee_id);
  const secondCommittee = committeesById.get(second.committee_id);
  if (firstCommittee && secondCommittee) {
    return compareCommittees(firstCommittee, secondCommittee);
  }
  return (firstCommittee?.name || first.committee_id).localeCompare(
    secondCommittee?.name || second.committee_id,
  );
}

function getAuthorityLevelClass(authorityLevel: string): string {
  return ["LOW", "MIDDLE", "HIGH"].includes(authorityLevel)
    ? authorityLevel.toLowerCase()
    : "";
}

function formatLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
