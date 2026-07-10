import { apiRequest } from "./client";
import type { NotificationSummaryRead } from "./types";

export function getMyNotifications(
  token: string,
  params: { includeInfo?: boolean; limit?: number } = {},
): Promise<NotificationSummaryRead> {
  const query = new URLSearchParams();
  if (params.includeInfo !== undefined) {
    query.set("include_info", String(params.includeInfo));
  }
  if (params.limit !== undefined) {
    query.set("limit", String(params.limit));
  }
  const queryString = query.toString();
  return apiRequest<NotificationSummaryRead>(
    `/notifications/my${queryString ? `?${queryString}` : ""}`,
    { token },
  );
}
