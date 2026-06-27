import { apiRequest } from "./client";
import type { AuditLogRead } from "./types";

interface AuditLogListParams {
  entityType?: string;
  entityId?: string;
  action?: string;
  changedByUserId?: string;
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
