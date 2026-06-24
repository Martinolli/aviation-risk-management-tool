import { apiRequest } from "./client";
import type { RiskRecordRead } from "./types";

type RiskListResponse = RiskRecordRead[] | { items?: RiskRecordRead[] };

export async function listRisks(token: string): Promise<RiskRecordRead[]> {
  const response = await apiRequest<RiskListResponse>("/risks", { token });

  if (Array.isArray(response)) {
    return response;
  }

  return Array.isArray(response.items) ? response.items : [];
}
