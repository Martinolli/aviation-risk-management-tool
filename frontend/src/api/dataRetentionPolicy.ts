import { apiRequest } from "./client";
import type { DataRetentionPolicyRead } from "./types";

export function getDataRetentionPolicy(
  token: string,
): Promise<DataRetentionPolicyRead> {
  return apiRequest<DataRetentionPolicyRead>("/data-retention-policy", { token });
}
