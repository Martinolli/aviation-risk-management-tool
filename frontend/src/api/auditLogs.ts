import { API_BASE_URL } from "../config/env";
import { ApiError, apiRequest } from "./client";
import type { AuditLogRead } from "./types";

export interface AuditLogListParams {
  entityType?: string;
  entityId?: string;
  action?: string;
  changedByUserId?: string;
  changedAtFrom?: string;
  changedAtTo?: string;
  limit?: number;
  offset?: number;
}

export async function listAuditLogs(
  token: string,
  params: AuditLogListParams = {},
): Promise<AuditLogRead[]> {
  const query = new URLSearchParams();

  if (params.entityType) {
    query.set("entity_type", params.entityType);
  }

  if (params.entityId) {
    query.set("entity_id", params.entityId);
  }

  if (params.action) {
    query.set("action", params.action);
  }

  if (params.changedByUserId) {
    query.set("changed_by_user_id", params.changedByUserId);
  }

  if (params.changedAtFrom) {
    query.set("changed_at_from", params.changedAtFrom);
  }

  if (params.changedAtTo) {
    query.set("changed_at_to", params.changedAtTo);
  }

  if (params.limit !== undefined) {
    query.set("limit", String(params.limit));
  }

  if (params.offset !== undefined) {
    query.set("offset", String(params.offset));
  }

  const queryString = query.toString();
  const path = queryString ? `/audit-logs?${queryString}` : "/audit-logs";
  const response = await apiRequest<
    AuditLogRead[] | { items?: AuditLogRead[] }
  >(path, { token });

  return Array.isArray(response) ? response : response.items ?? [];
}

export function getAuditLog(
  token: string,
  auditLogId: string,
): Promise<AuditLogRead> {
  return apiRequest<AuditLogRead>(
    `/audit-logs/${encodeURIComponent(auditLogId)}`,
    { token },
  );
}

export function exportAuditLogsCsv(
  token: string,
  params: AuditLogListParams = {},
): Promise<{ blob: Blob; filename: string }> {
  return downloadAuditExport(token, "/audit-logs/export/csv", params, "csv");
}

export function exportAuditLogsDocx(
  token: string,
  params: AuditLogListParams = {},
): Promise<{ blob: Blob; filename: string }> {
  return downloadAuditExport(token, "/audit-logs/export/docx", params, "docx");
}

async function downloadAuditExport(
  token: string,
  path: string,
  params: AuditLogListParams,
  fallbackExtension: "csv" | "docx",
): Promise<{ blob: Blob; filename: string }> {
  const queryString = buildAuditLogQuery(params).toString();
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
    ) ?? `audit-trail-export.${fallbackExtension}`;

  return { blob, filename };
}

function buildAuditLogQuery(params: AuditLogListParams): URLSearchParams {
  const query = new URLSearchParams();

  appendQueryParam(query, "entity_type", params.entityType);
  appendQueryParam(query, "entity_id", params.entityId);
  appendQueryParam(query, "action", params.action);
  appendQueryParam(query, "changed_by_user_id", params.changedByUserId);
  appendQueryParam(query, "changed_at_from", params.changedAtFrom);
  appendQueryParam(query, "changed_at_to", params.changedAtTo);
  appendQueryParam(query, "limit", params.limit);
  appendQueryParam(query, "offset", params.offset);

  return query;
}

function appendQueryParam(
  query: URLSearchParams,
  name: string,
  value: number | string | null | undefined,
): void {
  if (value === undefined || value === null || value === "") {
    return;
  }

  query.set(name, String(value));
}

async function buildDownloadError(response: Response): Promise<ApiError> {
  let message = "Unable to export audit trail.";
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
    "AUDIT_EXPORT_DOWNLOAD_ERROR",
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
