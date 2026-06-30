import { apiRequest } from "./client";
import type { UserRead } from "./types";

type UserListResponse = UserRead[] | { items?: UserRead[] };

export async function listUsers(
  token: string,
  params: { includeInactive?: boolean } = {},
): Promise<UserRead[]> {
  const query = new URLSearchParams();

  if (params.includeInactive !== undefined) {
    query.set("include_inactive", String(params.includeInactive));
  }

  const queryString = query.toString();
  const path = queryString ? `/users?${queryString}` : "/users";
  const response = await apiRequest<UserListResponse>(path, { token });

  return Array.isArray(response) ? response : response.items ?? [];
}

export function getUser(token: string, userId: string): Promise<UserRead> {
  return apiRequest<UserRead>(`/users/${encodeURIComponent(userId)}`, { token });
}
