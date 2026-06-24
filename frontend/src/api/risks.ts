import { apiRequest } from "./client";
import type {
  RiskCreateRequest,
  RiskDetailResponse,
  RiskRecordRead,
  RiskSubmitRequest,
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

export function submitRisk(
  token: string,
  riskRecordId: string,
  request: RiskSubmitRequest = {},
): Promise<RiskRecordRead> {
  return apiRequest<RiskRecordRead>(
    `/risks/${encodeURIComponent(riskRecordId)}/submit`,
    {
      method: "POST",
      body: request,
      token,
    },
  );
}
