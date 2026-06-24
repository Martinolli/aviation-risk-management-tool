import { apiRequest } from "./client";
import type { RiskDecisionCreateRequest, RiskDecisionRead } from "./types";

export function createRiskDecision(
  token: string,
  request: RiskDecisionCreateRequest,
): Promise<RiskDecisionRead> {
  return apiRequest<RiskDecisionRead>("/risk-decisions", {
    method: "POST",
    body: request,
    token,
  });
}
