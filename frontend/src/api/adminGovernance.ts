import { apiRequest } from "./client";
import type {
  CommitteeMemberRead,
  CommitteeRead,
  UserRead,
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

function withQuery(path: string, query: URLSearchParams): string {
  const queryString = query.toString();
  return queryString ? `${path}?${queryString}` : path;
}
