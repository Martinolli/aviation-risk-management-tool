import { apiRequest } from "./client";
import type { CommitteeRead } from "./types";

type CommitteeListResponse = CommitteeRead[] | { items?: CommitteeRead[] };

const AUTHORITY_LEVEL_ORDER: Record<string, number> = {
  LOW: 0,
  MIDDLE: 1,
  HIGH: 2,
};

export async function listCommittees(
  token: string,
  params: { includeArchived?: boolean } = {},
): Promise<CommitteeRead[]> {
  const query = new URLSearchParams();
  if (params.includeArchived !== undefined) {
    query.set("include_archived", String(params.includeArchived));
  }
  const queryString = query.toString();
  const path = queryString ? `/committees?${queryString}` : "/committees";
  const response = await apiRequest<CommitteeListResponse>(path, { token });
  const committees = Array.isArray(response) ? response : response.items ?? [];

  return committees
    .filter((committee) => params.includeArchived || committee.is_active)
    .sort((first, second) => {
      const authorityDifference =
        (AUTHORITY_LEVEL_ORDER[first.authority_level] ?? Number.MAX_SAFE_INTEGER) -
        (AUTHORITY_LEVEL_ORDER[second.authority_level] ?? Number.MAX_SAFE_INTEGER);

      return authorityDifference || first.name.localeCompare(second.name);
    });
}
