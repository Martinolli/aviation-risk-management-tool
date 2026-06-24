import { apiRequest } from "./client";
import type {
  RiskCreateRequest,
  RiskDetailResponse,
  RiskRecordRead,
} from "./types";

type RiskListResponse = RiskRecordRead[] | { items?: RiskRecordRead[] };

export async function listRisks(token: string): Promise<RiskRecordRead[]> {
  const response = await apiRequest<RiskListResponse>("/risks", { token });

  if (Array.isArray(response)) {
    return response;
  }

  return Array.isArray(response.items) ? response.items : [];
}

export function createRisk(
  token: string,
  request: RiskCreateRequest,
): Promise<RiskRecordRead> {
  return apiRequest<RiskRecordRead>("/risks", {
    method: "POST",
    body: request,
    token,
  });
}

export function getRiskDetail(
  token: string,
  riskRecordId: string,
): Promise<RiskDetailResponse> {
  return apiRequest<RiskDetailResponse>(
    `/risks/${encodeURIComponent(riskRecordId)}/detail`,
    { token },
  );
}
