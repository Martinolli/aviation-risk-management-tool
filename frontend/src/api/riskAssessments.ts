import { apiRequest } from "./client";
import type { RiskAssessmentCreateRequest, RiskAssessmentRead } from "./types";

export function createRiskAssessment(
  token: string,
  request: RiskAssessmentCreateRequest,
): Promise<RiskAssessmentRead> {
  return apiRequest<RiskAssessmentRead>("/risk-assessments", {
    method: "POST",
    body: request,
    token,
  });
}
