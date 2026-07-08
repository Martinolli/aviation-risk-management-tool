import { apiRequest } from "./client";
import type {
  RiskCreateRequest,
  RiskDetailResponse,
  RiskRecordRead,
  RiskSubmitRequest,
  RiskUpdateRequest,
} from "./types";

type RiskListResponse = RiskRecordRead[] | { items?: RiskRecordRead[] };

export interface RiskListParams {
  includeArchived?: boolean;
  search?: string;
  riskId?: string;
  domain?: string;
  boardOfOriginId?: string;
  workflowStatus?: string;
  lifecycleStatus?: string;
  ownerUserId?: string;
  createdByUserId?: string;
  latestRiskLevel?: string;
  hasOverdueActions?: boolean | null;
  hasDueOrOverdueMonitoring?: boolean | null;
  sortBy?: string;
  sortDirection?: "asc" | "desc";
}

export async function listRisks(
  token: string,
  params: RiskListParams = {},
): Promise<RiskRecordRead[]> {
  const query = new URLSearchParams();
  appendQueryParam(query, "include_archived", params.includeArchived);
  appendQueryParam(query, "search", params.search);
  appendQueryParam(query, "risk_id", params.riskId);
  appendQueryParam(query, "domain", params.domain);
  appendQueryParam(query, "board_of_origin_id", params.boardOfOriginId);
  appendQueryParam(query, "workflow_status", params.workflowStatus);
  appendQueryParam(query, "lifecycle_status", params.lifecycleStatus);
  appendQueryParam(query, "owner_user_id", params.ownerUserId);
  appendQueryParam(query, "created_by_user_id", params.createdByUserId);
  appendQueryParam(query, "latest_risk_level", params.latestRiskLevel);
  appendQueryParam(query, "has_overdue_actions", params.hasOverdueActions);
  appendQueryParam(
    query,
    "has_due_or_overdue_monitoring",
    params.hasDueOrOverdueMonitoring,
  );
  appendQueryParam(query, "sort_by", params.sortBy);
  appendQueryParam(query, "sort_direction", params.sortDirection);

  const queryString = query.toString();
  const path = queryString ? `/risks?${queryString}` : "/risks";
  const response = await apiRequest<RiskListResponse>(path, { token });

  if (Array.isArray(response)) {
    return response;
  }

  return Array.isArray(response.items) ? response.items : [];
}

function appendQueryParam(
  query: URLSearchParams,
  name: string,
  value: boolean | string | null | undefined,
) {
  if (value === undefined || value === null || value === "") {
    return;
  }

  query.set(name, String(value));
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

export function updateRisk(
  token: string,
  riskRecordId: string,
  request: RiskUpdateRequest,
): Promise<RiskRecordRead> {
  return apiRequest<RiskRecordRead>(
    `/risks/${encodeURIComponent(riskRecordId)}`,
    {
      method: "PATCH",
      body: request,
      token,
    },
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
