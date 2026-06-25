import { apiRequest } from "./client";
import type { CommitteeMemberRead } from "./types";

type CommitteeMemberListResponse =
  | CommitteeMemberRead[]
  | { items?: CommitteeMemberRead[] };

interface CommitteeMemberListParams {
  committeeId?: string;
  userId?: string;
  includeInactive?: boolean;
}

export async function listCommitteeMembers(
  token: string,
  params: CommitteeMemberListParams = {},
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

  const queryString = query.toString();
  const path = queryString ? `/committee-members?${queryString}` : "/committee-members";
  const response = await apiRequest<CommitteeMemberListResponse>(path, { token });

  return Array.isArray(response) ? response : response.items ?? [];
}
