import { apiRequest } from "./client";
import type { ManagementDashboardRead } from "./types";

export function getManagementDashboard(
  token: string,
  params: { limit?: number; highRiskLevels?: string[] } = {},
): Promise<ManagementDashboardRead> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) {
    query.set("limit", String(params.limit));
  }
  params.highRiskLevels?.forEach((level) => {
    query.append("high_risk_levels", level);
  });
  const queryString = query.toString();
  return apiRequest<ManagementDashboardRead>(
    `/management-dashboard${queryString ? `?${queryString}` : ""}`,
    { token },
  );
}
