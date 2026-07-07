import { apiRequest } from "./client";
import type {
  CommitteeArchiveRequest,
  CommitteeCreateRequest,
  CommitteeMemberCreateRequest,
  CommitteeMemberRead,
  CommitteeMemberUpdateRequest,
  CommitteeRead,
  CommitteeUpdateRequest,
  UserCreateRequest,
  UserRead,
  UserUpdateRequest,
} from "./types";

type UserListResponse = UserRead[] | { items?: UserRead[] };
type CommitteeListResponse = CommitteeRead[] | { items?: CommitteeRead[] };
type CommitteeMemberListResponse =
  | CommitteeMemberRead[]
  | { items?: CommitteeMemberRead[] };

export async function listAdminGovernanceUsers(
  token: string,
  params: { includeInactive?: boolean } = {},
): Promise<UserRead[]> {
  const query = new URLSearchParams();
  if (params.includeInactive !== undefined) {
    query.set("include_inactive", String(params.includeInactive));
  }
  const response = await apiRequest<UserListResponse>(
    withQuery("/admin/governance/users", query),
    { token },
  );
  return Array.isArray(response) ? response : response.items ?? [];
}

export async function listAdminGovernanceCommittees(
  token: string,
  params: { includeArchived?: boolean } = {},
): Promise<CommitteeRead[]> {
  const query = new URLSearchParams();
  if (params.includeArchived !== undefined) {
    query.set("include_archived", String(params.includeArchived));
  }
  const response = await apiRequest<CommitteeListResponse>(
    withQuery("/admin/governance/committees", query),
    { token },
  );
  return Array.isArray(response) ? response : response.items ?? [];
}

export async function listAdminGovernanceCommitteeMembers(
  token: string,
  params: {
    committeeId?: string;
    userId?: string;
    includeInactive?: boolean;
  } = {},
): Promise<CommitteeMemberRead[]> {
  const query = new URLSearchParams();
  if (params.committeeId) {
    query.set("committee_id", params.committeeId);
  }
  if (params.userId) {
    query.set("user_id", params.userId);
  }
  if (params.includeInactive !== undefined) {
    query.set("include_inactive", String(params.includeInactive));
  }
  const response = await apiRequest<CommitteeMemberListResponse>(
    withQuery("/admin/governance/committee-members", query),
    { token },
  );
  return Array.isArray(response) ? response : response.items ?? [];
}

export function createAdminUser(
  token: string,
  request: UserCreateRequest,
): Promise<UserRead> {
  return apiRequest<UserRead>("/users", {
    method: "POST",
    token,
    body: request,
  });
}

export function updateAdminUser(
  token: string,
  userId: string,
  request: UserUpdateRequest,
): Promise<UserRead> {
  return apiRequest<UserRead>(`/users/${encodeURIComponent(userId)}`, {
    method: "PATCH",
    token,
    body: request,
  });
}

export function createAdminCommittee(
  token: string,
  request: CommitteeCreateRequest,
): Promise<CommitteeRead> {
  return apiRequest<CommitteeRead>("/committees", {
    method: "POST",
    token,
    body: request,
  });
}

export function updateAdminCommittee(
  token: string,
  committeeId: string,
  request: CommitteeUpdateRequest,
): Promise<CommitteeRead> {
  return apiRequest<CommitteeRead>(
    `/committees/${encodeURIComponent(committeeId)}`,
    {
      method: "PATCH",
      token,
      body: request,
    },
  );
}

export function archiveAdminCommittee(
  token: string,
  committeeId: string,
  request: CommitteeArchiveRequest,
): Promise<CommitteeRead> {
  return apiRequest<CommitteeRead>(
    `/committees/${encodeURIComponent(committeeId)}/archive`,
    {
      method: "POST",
      token,
      body: request,
    },
  );
}

export function createAdminCommitteeMember(
  token: string,
  request: CommitteeMemberCreateRequest,
): Promise<CommitteeMemberRead> {
  return apiRequest<CommitteeMemberRead>("/committee-members", {
    method: "POST",
    token,
    body: request,
  });
}

export function updateAdminCommitteeMember(
  token: string,
  committeeMemberId: string,
  request: CommitteeMemberUpdateRequest,
): Promise<CommitteeMemberRead> {
  return apiRequest<CommitteeMemberRead>(
    `/committee-members/${encodeURIComponent(committeeMemberId)}`,
    {
      method: "PATCH",
      token,
      body: request,
    },
  );
}

function withQuery(path: string, query: URLSearchParams): string {
  const queryString = query.toString();
  return queryString ? `${path}?${queryString}` : path;
}
