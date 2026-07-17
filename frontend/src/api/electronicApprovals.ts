import { apiRequest } from "./client";
import type {
  ElectronicApprovalCreateRequest,
  ElectronicApprovalRead,
  ElectronicApprovalTargetType,
} from "./types";

export interface ElectronicApprovalListParams {
  targetType?: ElectronicApprovalTargetType;
  targetId?: string;
  riskRecordId?: string;
  approvedByUserId?: string;
}

export function createElectronicApproval(
  token: string,
  data: ElectronicApprovalCreateRequest,
): Promise<ElectronicApprovalRead> {
  return apiRequest<ElectronicApprovalRead>("/electronic-approvals", {
    method: "POST",
    body: data,
    token,
  });
}

export function listElectronicApprovals(
  token: string,
  params: ElectronicApprovalListParams = {},
): Promise<ElectronicApprovalRead[]> {
  const query = new URLSearchParams();
  appendQueryParam(query, "target_type", params.targetType);
  appendQueryParam(query, "target_id", params.targetId);
  appendQueryParam(query, "risk_record_id", params.riskRecordId);
  appendQueryParam(query, "approved_by_user_id", params.approvedByUserId);
  const queryString = query.toString();
  return apiRequest<ElectronicApprovalRead[]>(
    `/electronic-approvals${queryString ? `?${queryString}` : ""}`,
    { token },
  );
}

export function getElectronicApproval(
  token: string,
  approvalId: string,
): Promise<ElectronicApprovalRead> {
  return apiRequest<ElectronicApprovalRead>(
    `/electronic-approvals/${encodeURIComponent(approvalId)}`,
    { token },
  );
}

function appendQueryParam(
  query: URLSearchParams,
  name: string,
  value: string | null | undefined,
) {
  if (value) {
    query.set(name, value);
  }
}
