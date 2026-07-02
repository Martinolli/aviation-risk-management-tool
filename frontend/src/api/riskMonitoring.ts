import { apiRequest } from "./client";
import type {
  RiskMonitoringReviewOutcome,
  RiskMonitoringReviewRead,
  RiskMonitoringStatus,
} from "./types";

export interface RiskMonitoringReviewCreateRequest {
  risk_record_id: string;
  monitoring_owner_user_id?: string | null;
  review_frequency?: string | null;
  next_review_date?: string | null;
  review_notes?: string | null;
  effectiveness_review?: string | null;
}

export interface RiskMonitoringReviewUpdateRequest {
  monitoring_owner_user_id?: string | null;
  review_frequency?: string | null;
  next_review_date?: string | null;
  status?: RiskMonitoringStatus | null;
  review_notes?: string | null;
  effectiveness_review?: string | null;
  review_outcome?: RiskMonitoringReviewOutcome | null;
}

export interface RiskMonitoringReviewCompleteRequest {
  effectiveness_review: string;
  review_outcome: RiskMonitoringReviewOutcome;
  next_review_date?: string | null;
  review_notes?: string | null;
}

export interface RiskMonitoringReviewCloseRequest {
  closure_reason?: string | null;
}

export function listRiskMonitoringReviews(
  token: string,
  riskRecordId: string,
  params: { includeInactive?: boolean } = {},
): Promise<RiskMonitoringReviewRead[]> {
  const query = new URLSearchParams();
  if (params.includeInactive) {
    query.set("include_inactive", "true");
  }
  const queryString = query.toString();
  return apiRequest<RiskMonitoringReviewRead[]>(
    `/risk-monitoring/risk/${encodeURIComponent(riskRecordId)}${
      queryString ? `?${queryString}` : ""
    }`,
    { token },
  );
}

export function createRiskMonitoringReview(
  token: string,
  request: RiskMonitoringReviewCreateRequest,
): Promise<RiskMonitoringReviewRead> {
  return apiRequest<RiskMonitoringReviewRead>("/risk-monitoring", {
    method: "POST",
    token,
    body: request,
  });
}

export function updateRiskMonitoringReview(
  token: string,
  monitoringReviewId: string,
  request: RiskMonitoringReviewUpdateRequest,
): Promise<RiskMonitoringReviewRead> {
  return apiRequest<RiskMonitoringReviewRead>(
    `/risk-monitoring/${encodeURIComponent(monitoringReviewId)}`,
    { method: "PATCH", token, body: request },
  );
}

export function completeRiskMonitoringReview(
  token: string,
  monitoringReviewId: string,
  request: RiskMonitoringReviewCompleteRequest,
): Promise<RiskMonitoringReviewRead> {
  return apiRequest<RiskMonitoringReviewRead>(
    `/risk-monitoring/${encodeURIComponent(monitoringReviewId)}/complete`,
    { method: "POST", token, body: request },
  );
}

export function closeRiskMonitoringReview(
  token: string,
  monitoringReviewId: string,
  request: RiskMonitoringReviewCloseRequest = {},
): Promise<RiskMonitoringReviewRead> {
  return apiRequest<RiskMonitoringReviewRead>(
    `/risk-monitoring/${encodeURIComponent(monitoringReviewId)}/close`,
    { method: "POST", token, body: request },
  );
}
