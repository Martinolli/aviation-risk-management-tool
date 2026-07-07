import { useEffect, useMemo, useState } from "react";
import { Navigate } from "react-router-dom";

import {
  archiveAdminCommittee,
  createAdminCommittee,
  createAdminCommitteeMember,
  createAdminUser,
  listAdminGovernanceCommitteeMembers,
  listAdminGovernanceCommittees,
  listAdminGovernanceUsers,
  updateAdminCommittee,
  updateAdminCommitteeMember,
  updateAdminUser,
} from "../api/adminGovernance";
import { ApiError } from "../api/client";
import type {
  CommitteeMemberRead,
  CommitteeRead,
  UserRead,
} from "../api/types";
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

const ADMIN_ACCESS_GUIDANCE =
  "Admin governance data is restricted to authorized governance administrators.";

export function AdminGovernancePage() {
  const { isAuthenticated, token, user: currentUser } = useAuth();
  const [governanceData, setGovernanceData] = useState<GovernanceDataState>({
    status: "loading",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [createUserForm, setCreateUserForm] = useState({
    display_name: "",
    email: "",
    password: "",
  });
  const [selectedUserId, setSelectedUserId] = useState("");
  const [userEditForm, setUserEditForm] = useState({
    display_name: "",
    is_active: true,
    password: "",
  });
  const [createCommitteeForm, setCreateCommitteeForm] = useState({
    name: "",
    description: "",
  });
  const [selectedCommitteeId, setSelectedCommitteeId] = useState("");
  const [committeeEditForm, setCommitteeEditForm] = useState({
    name: "",
    description: "",
    is_active: true,
    archive_reason: "",
  });
  const [membershipForm, setMembershipForm] = useState({
    committee_id: "",
    user_id: "",
    role_label: "",
  });
  const [membershipRoleDrafts, setMembershipRoleDrafts] = useState<
    Record<string, string>
  >({});

  async function loadGovernanceData(tokenToUse: string) {
    setGovernanceData((current) =>
      current.status === "success" ? current : { status: "loading" },
    );
    try {
      const [users, committees, memberships] = await Promise.all([
        listAdminGovernanceUsers(tokenToUse, { includeInactive: true }),
        listAdminGovernanceCommittees(tokenToUse, { includeArchived: true }),
        listAdminGovernanceCommitteeMembers(tokenToUse, {
          includeInactive: true,
        }),
      ]);
      setGovernanceData({
        status: "success",
        users,
        committees,
        memberships,
      });
      setMembershipRoleDrafts((current) => {
        const next = { ...current };
        for (const membership of memberships) {
          next[membership.id] = next[membership.id] ?? membership.role_label ?? "";
        }
        return next;
      });
      setMembershipForm((current) => ({
        ...current,
        committee_id:
          current.committee_id ||
          committees.find((committee) => committee.is_active)?.id ||
          "",
        user_id:
          current.user_id || users.find((listedUser) => listedUser.is_active)?.id || "",
      }));
    } catch (error) {
      setGovernanceData({
        status: "error",
        message:
          error instanceof ApiError
            ? error.message
            : "Please try again shortly.",
      });
    }
  }

  useEffect(() => {
    if (!token) {
      return;
    }
    void loadGovernanceData(token);
  }, [token]);

  const data =
    governanceData.status === "success"
      ? governanceData
      : { users: [], committees: [], memberships: [] };
  const users = data.users;
  const committees = data.committees;
  const memberships = data.memberships;
  const usersById = useMemo(
    () => new Map(users.map((listedUser) => [listedUser.id, listedUser])),
    [users],
  );
  const committeesById = useMemo(
    () => new Map(committees.map((committee) => [committee.id, committee])),
    [committees],
  );
  const sortedUsers = useMemo(() => [...users].sort(compareUsers), [users]);
  const sortedCommittees = useMemo(
    () => [...committees].sort(compareCommittees),
    [committees],
  );
  const activeUsers = sortedUsers.filter((listedUser) => listedUser.is_active);
  const activeCommittees = sortedCommittees.filter(
    (committee) => committee.is_active,
  );
  const selectedCommitteeMembers = memberships
    .filter((membership) => membership.committee_id === membershipForm.committee_id)
    .sort((first, second) => compareMemberships(first, second, usersById));
  const selectedUser = usersById.get(selectedUserId);
  const selectedCommittee = committeesById.get(selectedCommitteeId);

  useEffect(() => {
    if (!selectedUser && sortedUsers[0]) {
      setSelectedUserId(sortedUsers[0].id);
    }
  }, [selectedUser, sortedUsers]);

  useEffect(() => {
    if (selectedUser) {
      setUserEditForm({
        display_name: selectedUser.display_name,
        is_active: selectedUser.is_active,
        password: "",
      });
    }
  }, [selectedUser]);

  useEffect(() => {
    const firstConfigurable = sortedCommittees.find(
      (committee) => !committee.is_fixed,
    );
    if (!selectedCommittee && firstConfigurable) {
      setSelectedCommitteeId(firstConfigurable.id);
    }
  }, [selectedCommittee, sortedCommittees]);

  useEffect(() => {
    if (selectedCommittee) {
      setCommitteeEditForm({
        name: selectedCommittee.name,
        description: selectedCommittee.description ?? "",
        is_active: selectedCommittee.is_active,
        archive_reason: "",
      });
    }
  }, [selectedCommittee]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }
  const adminToken = token;

  async function runAdminAction(
    success: string,
    action: () => Promise<void>,
  ): Promise<void> {
    if (!token) {
      return;
    }
    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await action();
      await loadGovernanceData(token);
      setSuccessMessage(success);
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to complete admin operation.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleCreateUser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAdminAction("User created.", async () => {
      await createAdminUser(adminToken, {
        display_name: createUserForm.display_name.trim(),
        email: createUserForm.email.trim(),
        password: createUserForm.password || null,
      });
      setCreateUserForm({ display_name: "", email: "", password: "" });
    });
  }

  async function handleUpdateUser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedUser) {
      return;
    }
    if (
      selectedUser.id === currentUser?.id &&
      selectedUser.is_active &&
      !userEditForm.is_active
    ) {
      setErrorMessage("Current user cannot be deactivated from this page.");
      return;
    }
    if (
      selectedUser.is_active &&
      !userEditForm.is_active &&
      !window.confirm("Deactivate this user?")
    ) {
      return;
    }
    await runAdminAction("User updated.", async () => {
      await updateAdminUser(adminToken, selectedUser.id, {
        display_name: userEditForm.display_name.trim(),
        is_active: userEditForm.is_active,
        password: userEditForm.password || undefined,
      });
    });
  }

  async function handleCreateCommittee(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAdminAction("Committee created.", async () => {
      await createAdminCommittee(adminToken, {
        name: createCommitteeForm.name.trim(),
        description: createCommitteeForm.description.trim() || null,
        authority_level: "LOW",
        committee_type: "OPERATIONAL_BOARD",
      });
      setCreateCommitteeForm({ name: "", description: "" });
    });
  }

  async function handleUpdateCommittee(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCommittee || selectedCommittee.is_fixed) {
      return;
    }
    await runAdminAction("Committee updated.", async () => {
      await updateAdminCommittee(adminToken, selectedCommittee.id, {
        name: committeeEditForm.name.trim(),
        description: committeeEditForm.description.trim() || null,
        is_active: committeeEditForm.is_active,
      });
    });
  }

  async function handleArchiveCommittee() {
    if (!selectedCommittee || selectedCommittee.is_fixed) {
      return;
    }
    if (!committeeEditForm.archive_reason.trim()) {
      setErrorMessage("Archive reason is required.");
      return;
    }
    if (!window.confirm("Archive this configurable committee?")) {
      return;
    }
    await runAdminAction("Committee archived.", async () => {
      await archiveAdminCommittee(adminToken, selectedCommittee.id, {
        archive_reason: committeeEditForm.archive_reason.trim(),
      });
    });
  }

  async function handleCreateMembership(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAdminAction("Committee membership added.", async () => {
      await createAdminCommitteeMember(adminToken, {
        committee_id: membershipForm.committee_id,
        user_id: membershipForm.user_id,
        role_label: membershipForm.role_label.trim() || null,
      });
      setMembershipForm((current) => ({ ...current, role_label: "" }));
    });
  }

  async function handleUpdateMembershipRole(membership: CommitteeMemberRead) {
    await runAdminAction("Committee membership updated.", async () => {
      await updateAdminCommitteeMember(adminToken, membership.id, {
        role_label: membershipRoleDrafts[membership.id]?.trim() || null,
      });
    });
  }

  async function handleToggleMembership(membership: CommitteeMemberRead) {
    if (
      membership.is_active &&
      !window.confirm("Deactivate this committee membership?")
    ) {
      return;
    }
    await runAdminAction(
      membership.is_active
        ? "Committee membership deactivated."
        : "Committee membership reactivated.",
      async () => {
        await updateAdminCommitteeMember(adminToken, membership.id, {
          is_active: !membership.is_active,
        });
      },
    );
  }

  return (
    <section
      className="admin-governance-page"
      aria-labelledby="admin-governance-heading"
    >
      <header className="page-header">
        <div>
          <p className="eyebrow">Admin Governance</p>
          <h1 id="admin-governance-heading">Governance management</h1>
          <p>
            Manage users, committees, Authority Levels, and committee
            memberships.
          </p>
        </div>
      </header>

      <p className="governance-access-note">{ADMIN_ACCESS_GUIDANCE}</p>

      {governanceData.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading governance data...
        </p>
      )}
      {governanceData.status === "error" && (
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong>Unable to load governance data.</strong>
          <span>{governanceData.message}</span>
        </div>
      )}
      {successMessage && (
        <p className="admin-success-message" role="status">
          {successMessage}
        </p>
      )}
      {errorMessage && (
        <p className="admin-error-message" role="alert">
          {errorMessage}
        </p>
      )}

      {governanceData.status === "success" && (
        <>
          <section className="admin-summary-grid" aria-label="Governance summary">
            <SummaryCard title="Users" value={users.length} detail={`${activeUsers.length} active`} />
            <SummaryCard title="Committees" value={committees.length} detail={`${activeCommittees.length} active`} />
            <SummaryCard title="Memberships" value={memberships.length} detail={`${memberships.filter((membership) => membership.is_active).length} active`} />
            <SummaryCard title="Active committees" value={activeCommittees.length} detail="Operational governance" />
            <SummaryCard title="Configurable LOW committees" value={committees.filter((committee) => committee.authority_level === "LOW" && !committee.is_fixed).length} detail="Configurable" />
            <SummaryCard title="Fixed / protected committees" value={committees.filter((committee) => committee.is_fixed).length} detail="Risk Management Committee / Executive Safety Management Committee" />
            <SummaryCard title="Inactive memberships" value={memberships.filter((membership) => !membership.is_active).length} detail="Inactive membership" />
          </section>

          <section className="admin-section" aria-labelledby="users-heading">
            <div className="admin-section-header">
              <div>
                <p className="eyebrow">User administration</p>
                <h2 id="users-heading">Users</h2>
              </div>
            </div>

            <form className="admin-form" onSubmit={handleCreateUser}>
              <h3>Create user</h3>
              <div className="admin-form-grid">
                <label>
                  Display name
                  <input
                    onChange={(event) =>
                      setCreateUserForm((current) => ({
                        ...current,
                        display_name: event.target.value,
                      }))
                    }
                    required
                    value={createUserForm.display_name}
                  />
                </label>
                <label>
                  Email
                  <input
                    onChange={(event) =>
                      setCreateUserForm((current) => ({
                        ...current,
                        email: event.target.value,
                      }))
                    }
                    required
                    type="email"
                    value={createUserForm.email}
                  />
                </label>
                <label>
                  Temporary password
                  <input
                    autoComplete="new-password"
                    onChange={(event) =>
                      setCreateUserForm((current) => ({
                        ...current,
                        password: event.target.value,
                      }))
                    }
                    type="password"
                    value={createUserForm.password}
                  />
                </label>
              </div>
              <div className="admin-inline-actions">
                <button disabled={isSubmitting} type="submit">
                  Create user
                </button>
              </div>
            </form>

            <div className="admin-control-row">
              <label>
                Select user
                <select
                  onChange={(event) => setSelectedUserId(event.target.value)}
                  value={selectedUserId}
                >
                  {sortedUsers.map((listedUser) => (
                    <option key={listedUser.id} value={listedUser.id}>
                      {listedUser.display_name} - {listedUser.email}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {selectedUser && (
              <form className="admin-edit-panel" onSubmit={handleUpdateUser}>
                <h3>Update user</h3>
                <p className="admin-warning-text">
                  Password fields are blank by design and are only sent when
                  entered.
                </p>
                <div className="admin-form-grid">
                  <label>
                    Display name
                    <input
                      onChange={(event) =>
                        setUserEditForm((current) => ({
                          ...current,
                          display_name: event.target.value,
                        }))
                      }
                      required
                      value={userEditForm.display_name}
                    />
                  </label>
                  <label>
                    New password
                    <input
                      autoComplete="new-password"
                      onChange={(event) =>
                        setUserEditForm((current) => ({
                          ...current,
                          password: event.target.value,
                        }))
                      }
                      type="password"
                      value={userEditForm.password}
                    />
                  </label>
                  <label className="admin-toggle">
                    <input
                      checked={userEditForm.is_active}
                      disabled={selectedUser.id === currentUser?.id}
                      onChange={(event) =>
                        setUserEditForm((current) => ({
                          ...current,
                          is_active: event.target.checked,
                        }))
                      }
                      type="checkbox"
                    />
                    Active user
                  </label>
                </div>
                {selectedUser.id === currentUser?.id && (
                  <p className="admin-warning-text">
                    Current user deactivation is disabled on this page.
                  </p>
                )}
                <div className="admin-inline-actions">
                  <button disabled={isSubmitting} type="submit">
                    Update user
                  </button>
                </div>
              </form>
            )}

            <div className="admin-managed-grid">
              {sortedUsers.map((listedUser) => (
                <article className="admin-managed-card" key={listedUser.id}>
                  <h3>{listedUser.display_name}</h3>
                  <p>{listedUser.email}</p>
                  <span
                    className={`governance-chip ${listedUser.is_active ? "" : "inactive"}`}
                  >
                    {listedUser.is_active ? "Active" : "Inactive"}
                  </span>
                </article>
              ))}
            </div>
          </section>

          <section className="admin-section" aria-labelledby="committees-heading">
            <div className="admin-section-header">
              <div>
                <p className="eyebrow">Committee administration</p>
                <h2 id="committees-heading">Committees</h2>
              </div>
            </div>

            <form className="admin-form" onSubmit={handleCreateCommittee}>
              <h3>Create configurable LOW committee</h3>
              <p className="protected-committee-note">
                MIDDLE and HIGH committees are protected governance entities and
                are not created here.
              </p>
              <div className="admin-form-grid">
                <label>
                  Name
                  <input
                    onChange={(event) =>
                      setCreateCommitteeForm((current) => ({
                        ...current,
                        name: event.target.value,
                      }))
                    }
                    required
                    value={createCommitteeForm.name}
                  />
                </label>
                <label>
                  Description
                  <textarea
                    onChange={(event) =>
                      setCreateCommitteeForm((current) => ({
                        ...current,
                        description: event.target.value,
                      }))
                    }
                    rows={3}
                    value={createCommitteeForm.description}
                  />
                </label>
                <label>
                  Authority Level
                  <select disabled value="LOW">
                    <option value="LOW">LOW</option>
                  </select>
                </label>
                <label>
                  Committee Type
                  <select disabled value="OPERATIONAL_BOARD">
                    <option value="OPERATIONAL_BOARD">OPERATIONAL_BOARD</option>
                  </select>
                </label>
              </div>
              <div className="admin-inline-actions">
                <button disabled={isSubmitting} type="submit">
                  Create committee
                </button>
              </div>
            </form>

            <div className="committee-governance-grid">
              {(["LOW", "MIDDLE", "HIGH"] as const).map((authorityLevel) => (
                <section
                  className="admin-managed-card"
                  key={authorityLevel}
                  aria-labelledby={`committee-group-${authorityLevel}`}
                >
                  <h3 id={`committee-group-${authorityLevel}`}>
                    Authority Level: {authorityLevel}
                  </h3>
                  {sortedCommittees
                    .filter(
                      (committee) => committee.authority_level === authorityLevel,
                    )
                    .map((committee) => (
                      <article className="admin-committee-row" key={committee.id}>
                        <div>
                          <strong>{committee.name}</strong>
                          <p>{committee.description || "No description"}</p>
                          <div className="committee-governance-metadata">
                            <span className="governance-chip">
                              {formatLabel(committee.committee_type)}
                            </span>
                            <span
                              className={`governance-chip ${committee.is_active ? "" : "inactive"}`}
                            >
                              {committee.is_active ? "Active" : "Inactive"}
                            </span>
                            <span className="governance-chip">
                              {committee.is_fixed
                                ? "Fixed / protected"
                                : "Configurable"}
                            </span>
                          </div>
                        </div>
                        {!committee.is_fixed ? (
                          <button
                            disabled={isSubmitting}
                            onClick={() => setSelectedCommitteeId(committee.id)}
                            type="button"
                          >
                            Edit
                          </button>
                        ) : (
                          <span className="protected-committee-note">
                            Read-only
                          </span>
                        )}
                      </article>
                    ))}
                </section>
              ))}
            </div>

            {selectedCommittee && !selectedCommittee.is_fixed && (
              <form className="admin-edit-panel" onSubmit={handleUpdateCommittee}>
                <h3>Update configurable committee</h3>
                <div className="admin-form-grid">
                  <label>
                    Name
                    <input
                      onChange={(event) =>
                        setCommitteeEditForm((current) => ({
                          ...current,
                          name: event.target.value,
                        }))
                      }
                      required
                      value={committeeEditForm.name}
                    />
                  </label>
                  <label>
                    Description
                    <textarea
                      onChange={(event) =>
                        setCommitteeEditForm((current) => ({
                          ...current,
                          description: event.target.value,
                        }))
                      }
                      rows={3}
                      value={committeeEditForm.description}
                    />
                  </label>
                  <label className="admin-toggle">
                    <input
                      checked={committeeEditForm.is_active}
                      onChange={(event) =>
                        setCommitteeEditForm((current) => ({
                          ...current,
                          is_active: event.target.checked,
                        }))
                      }
                      type="checkbox"
                    />
                    Active committee
                  </label>
                </div>
                <div className="admin-inline-actions">
                  <button disabled={isSubmitting} type="submit">
                    Update committee
                  </button>
                </div>
                <div className="admin-danger-zone">
                  <label>
                    Archive reason
                    <textarea
                      onChange={(event) =>
                        setCommitteeEditForm((current) => ({
                          ...current,
                          archive_reason: event.target.value,
                        }))
                      }
                      rows={2}
                      value={committeeEditForm.archive_reason}
                    />
                  </label>
                  <button
                    disabled={isSubmitting}
                    onClick={() => void handleArchiveCommittee()}
                    type="button"
                  >
                    Archive configurable committee
                  </button>
                </div>
              </form>
            )}
          </section>

          <section className="admin-section membership-manager" aria-labelledby="memberships-heading">
            <div className="admin-section-header">
              <div>
                <p className="eyebrow">Committee membership</p>
                <h2 id="memberships-heading">Committee memberships</h2>
              </div>
            </div>

            <form className="admin-form" onSubmit={handleCreateMembership}>
              <h3>Add committee membership</h3>
              <div className="admin-form-grid">
                <label>
                  Committee
                  <select
                    onChange={(event) =>
                      setMembershipForm((current) => ({
                        ...current,
                        committee_id: event.target.value,
                      }))
                    }
                    required
                    value={membershipForm.committee_id}
                  >
                    <option value="">Select committee</option>
                    {activeCommittees.map((committee) => (
                      <option key={committee.id} value={committee.id}>
                        {committee.name} - {committee.authority_level}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  User
                  <select
                    onChange={(event) =>
                      setMembershipForm((current) => ({
                        ...current,
                        user_id: event.target.value,
                      }))
                    }
                    required
                    value={membershipForm.user_id}
                  >
                    <option value="">Select active user</option>
                    {activeUsers.map((listedUser) => (
                      <option key={listedUser.id} value={listedUser.id}>
                        {listedUser.display_name} - {listedUser.email}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Role label
                  <input
                    onChange={(event) =>
                      setMembershipForm((current) => ({
                        ...current,
                        role_label: event.target.value,
                      }))
                    }
                    value={membershipForm.role_label}
                  />
                </label>
              </div>
              <div className="admin-inline-actions">
                <button disabled={isSubmitting} type="submit">
                  Add membership
                </button>
              </div>
            </form>

            <div className="membership-list">
              {selectedCommitteeMembers.length === 0 ? (
                <p className="governance-empty">
                  No committee membership records for the selected committee.
                </p>
              ) : (
                selectedCommitteeMembers.map((membership) => {
                  const memberUser = usersById.get(membership.user_id);
                  return (
                    <article className="admin-managed-card" key={membership.id}>
                      <div className="committee-member-identity">
                        <strong>{memberUser?.display_name || membership.user_id}</strong>
                        <span>{memberUser?.email || "Unknown email"}</span>
                      </div>
                      <span
                        className={`governance-chip ${membership.is_active ? "" : "inactive"}`}
                      >
                        {membership.is_active
                          ? "Active membership"
                          : "Inactive membership"}
                      </span>
                      <div className="admin-control-row">
                        <label>
                          Role label
                          <input
                            onChange={(event) =>
                              setMembershipRoleDrafts((current) => ({
                                ...current,
                                [membership.id]: event.target.value,
                              }))
                            }
                            value={
                              membershipRoleDrafts[membership.id] ??
                              membership.role_label ??
                              ""
                            }
                          />
                        </label>
                      </div>
                      <div className="admin-inline-actions">
                        <button
                          disabled={isSubmitting}
                          onClick={() => void handleUpdateMembershipRole(membership)}
                          type="button"
                        >
                          Update role
                        </button>
                        <button
                          disabled={isSubmitting}
                          onClick={() => void handleToggleMembership(membership)}
                          type="button"
                        >
                          {membership.is_active ? "Deactivate" : "Reactivate"}
                        </button>
                      </div>
                    </article>
                  );
                })
              )}
            </div>
          </section>
        </>
      )}
    </section>
  );
}

function SummaryCard({
  title,
  value,
  detail,
}: {
  title: string;
  value: number;
  detail: string;
}) {
  return (
    <article className="admin-summary-card">
      <h2>{title}</h2>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
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
  return (usersById.get(first.user_id)?.display_name || first.user_id).localeCompare(
    usersById.get(second.user_id)?.display_name || second.user_id,
  );
}

function formatLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
