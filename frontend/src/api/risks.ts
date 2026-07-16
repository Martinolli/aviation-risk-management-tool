import { API_BASE_URL } from "../config/env";
import { ApiError, apiRequest } from "./client";
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
  const query = buildRiskListQuery(params);
  const queryString = query.toString();
  const path = queryString ? `/risks?${queryString}` : "/risks";
  const response = await apiRequest<RiskListResponse>(path, { token });

  if (Array.isArray(response)) {
    return response;
  }

  return Array.isArray(response.items) ? response.items : [];
}

export function exportRiskRegisterCsv(
  token: string,
  params: RiskListParams = {},
): Promise<{ blob: Blob; filename: string }> {
  return downloadRiskRegisterExport(token, "/risks/export/csv", params, "csv");
}

export function exportRiskRegisterDocx(
  token: string,
  params: RiskListParams = {},
): Promise<{ blob: Blob; filename: string }> {
  return downloadRiskRegisterExport(token, "/risks/export/docx", params, "docx");
}

export function buildRiskListQuery(params: RiskListParams): URLSearchParams {
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
  return query;
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

async function downloadRiskRegisterExport(
  token: string,
  path: string,
  params: RiskListParams,
  fallbackExtension: "csv" | "docx",
): Promise<{ blob: Blob; filename: string }> {
  const queryString = buildRiskListQuery(params).toString();
  const url = `${API_BASE_URL}${path}${queryString ? `?${queryString}` : ""}`;

  let response: Response;
  try {
    response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch {
    throw new ApiError("Unable to reach the API.", 0, "NETWORK_ERROR", {});
  }

  if (!response.ok) {
    throw await buildDownloadError(response);
  }

  const blob = await response.blob();
  const filename =
    getFilenameFromContentDisposition(
      response.headers.get("content-disposition"),
    ) ?? `risk-register-export.${fallbackExtension}`;

  return { blob, filename };
}

async function buildDownloadError(response: Response): Promise<ApiError> {
  let message = "Unable to export risk register.";
  let details: unknown = {};

  try {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const body = await response.json();
      details = body;
      if (
        body &&
        typeof body === "object" &&
        "error" in body &&
        body.error &&
        typeof body.error === "object" &&
        "message" in body.error &&
        typeof body.error.message === "string"
      ) {
        message = body.error.message;
      }
    } else {
      const text = await response.text();
      details = text;
      if (text) {
        message = text;
      }
    }
  } catch {
    // Keep the default export message if the response body cannot be parsed.
  }

  return new ApiError(
    message,
    response.status,
    "RISK_REGISTER_EXPORT_DOWNLOAD_ERROR",
    details,
  );
}

function getFilenameFromContentDisposition(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const filenameStarMatch = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (filenameStarMatch?.[1]) {
    return decodeURIComponent(filenameStarMatch[1].replace(/"/g, ""));
  }

  const filenameMatch = value.match(/filename="?([^";]+)"?/i);
  return filenameMatch?.[1] ?? null;
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
