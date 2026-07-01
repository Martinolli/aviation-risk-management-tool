import { API_BASE_URL } from "../config/env";
import { ApiError, apiRequest } from "./client";
import type {
  RiskEvidenceArchiveRequest,
  RiskEvidenceRead,
} from "./types";

export function listRiskEvidence(
  token: string,
  riskRecordId: string,
  params: { includeArchived?: boolean } = {},
): Promise<RiskEvidenceRead[]> {
  const query = new URLSearchParams();
  if (params.includeArchived) {
    query.set("include_archived", "true");
  }
  const queryString = query.toString();
  return apiRequest<RiskEvidenceRead[]>(
    `/risk-evidence/risk/${encodeURIComponent(riskRecordId)}${
      queryString ? `?${queryString}` : ""
    }`,
    { token },
  );
}

export function uploadRiskEvidence(
  token: string,
  riskRecordId: string,
  file: File,
  description?: string,
): Promise<RiskEvidenceRead> {
  const formData = new FormData();
  formData.append("file", file);
  if (description?.trim()) {
    formData.append("description", description.trim());
  }

  return apiRequest<RiskEvidenceRead>(
    `/risk-evidence/${encodeURIComponent(riskRecordId)}/upload`,
    {
      method: "POST",
      token,
      body: formData,
    },
  );
}

export function archiveRiskEvidence(
  token: string,
  evidenceId: string,
  request: RiskEvidenceArchiveRequest = {},
): Promise<RiskEvidenceRead> {
  return apiRequest<RiskEvidenceRead>(
    `/risk-evidence/${encodeURIComponent(evidenceId)}/archive`,
    {
      method: "POST",
      token,
      body: request,
    },
  );
}

export async function downloadRiskEvidence(
  token: string,
  evidenceId: string,
): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/risk-evidence/${encodeURIComponent(evidenceId)}/download`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
  } catch {
    throw new ApiError("Unable to reach the API.", 0, "NETWORK_ERROR", {});
  }

  if (!response.ok) {
    let details: unknown = {};
    let message = "Unable to download evidence.";
    try {
      details = await response.json();
      if (
        details &&
        typeof details === "object" &&
        "error" in details &&
        details.error &&
        typeof details.error === "object" &&
        "message" in details.error &&
        typeof details.error.message === "string"
      ) {
        message = details.error.message;
      }
    } catch {
      // Preserve the default message when the response has no JSON error body.
    }
    throw new ApiError(
      message,
      response.status,
      "EVIDENCE_DOWNLOAD_ERROR",
      details,
    );
  }

  return response.blob();
}
