import { apiRequest } from "./client";
import type { CommitteeRead } from "./types";

type CommitteeListResponse = CommitteeRead[] | { items?: CommitteeRead[] };

const AUTHORITY_LEVEL_ORDER: Record<string, number> = {
  LOW: 0,
  MIDDLE: 1,
  HIGH: 2,
};

export async function listCommittees(token: string): Promise<CommitteeRead[]> {
  const response = await apiRequest<CommitteeListResponse>("/committees", {
    token,
  });
  const committees = Array.isArray(response) ? response : response.items ?? [];

  return committees
    .filter((committee) => committee.is_active)
    .sort((first, second) => {
      const authorityDifference =
        (AUTHORITY_LEVEL_ORDER[first.authority_level] ?? Number.MAX_SAFE_INTEGER) -
        (AUTHORITY_LEVEL_ORDER[second.authority_level] ?? Number.MAX_SAFE_INTEGER);

      return authorityDifference || first.name.localeCompare(second.name);
    });
}
