import { apiRequest } from "./client";
import type {
  RiskActionCompleteRequest,
  RiskActionCreateRequest,
  RiskActionRead,
} from "./types";

export function createRiskAction(
  token: string,
  request: RiskActionCreateRequest,
): Promise<RiskActionRead> {
  return apiRequest<RiskActionRead>("/risk-actions", {
    method: "POST",
    body: request,
    token,
  });
}

export function completeRiskAction(
  token: string,
  riskActionId: string,
  request: RiskActionCompleteRequest,
): Promise<RiskActionRead> {
  return apiRequest<RiskActionRead>(
    `/risk-actions/${encodeURIComponent(riskActionId)}/complete`,
    {
      method: "POST",
      body: request,
      token,
    },
  );
}
