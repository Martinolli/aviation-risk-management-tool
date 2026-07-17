import { apiRequest } from "./client";
import type { PermissionMatrixRead } from "./types";

export function getPermissionMatrix(
  token: string,
): Promise<PermissionMatrixRead> {
  return apiRequest<PermissionMatrixRead>("/permission-matrix", { token });
}
