import { apiRequest } from "./client";
import type {
  RiskActionCompleteRequest,
  RiskActionCreateRequest,
  RiskActionRead,
} from "./types";

export function listRiskActions(
  token: string,
  params: {
    riskRecordId?: string;
    includeCompleted?: boolean;
    includeCancelled?: boolean;
  } = {},
): Promise<RiskActionRead[]> {
  const query = new URLSearchParams();
  if (params.riskRecordId) {
    query.set("risk_record_id", params.riskRecordId);
  }
  if (params.includeCompleted !== undefined) {
    query.set("include_completed", String(params.includeCompleted));
  }
  if (params.includeCancelled !== undefined) {
    query.set("include_cancelled", String(params.includeCancelled));
  }
  const queryString = query.toString();
  return apiRequest<RiskActionRead[]>(
    `/risk-actions${queryString ? `?${queryString}` : ""}`,
    { token },
  );
}

export function listMyRiskActions(
  token: string,
  params: {
    includeCompleted?: boolean;
    includeCancelled?: boolean;
  } = {},
): Promise<RiskActionRead[]> {
  const query = new URLSearchParams();
  if (params.includeCompleted !== undefined) {
    query.set("include_completed", String(params.includeCompleted));
  }
  if (params.includeCancelled !== undefined) {
    query.set("include_cancelled", String(params.includeCancelled));
  }
  const queryString = query.toString();
  return apiRequest<RiskActionRead[]>(
    `/risk-actions/my${queryString ? `?${queryString}` : ""}`,
    { token },
  );
}

export function getRiskAction(
  token: string,
  riskActionId: string,
): Promise<RiskActionRead> {
  return apiRequest<RiskActionRead>(
    `/risk-actions/${encodeURIComponent(riskActionId)}`,
    { token },
  );
}

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
