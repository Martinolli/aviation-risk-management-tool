import { apiRequest } from "./client";
import type { RiskActionCreateRequest, RiskActionRead } from "./types";

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
