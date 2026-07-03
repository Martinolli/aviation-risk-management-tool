import { API_BASE_URL } from "../config/env";
import { ApiError, apiRequest } from "./client";
import type { GeneratedReportRead } from "./types";

type GeneratedReportListResponse =
  | GeneratedReportRead[]
  | { items?: GeneratedReportRead[] };

interface GeneratedReportListParams {
  riskRecordId?: string;
  reportType?: string;
}

export interface GenerateCommitteeMeetingPackRequest {
  output_dir?: string | null;
  meeting_title?: string | null;
  meeting_date?: string | null;
}

export function generateRiskDossierReport(
  token: string,
  riskRecordId: string,
): Promise<GeneratedReportRead> {
  return apiRequest<GeneratedReportRead>(
    `/reports/risk-dossiers/${encodeURIComponent(riskRecordId)}`,
    {
      method: "POST",
      token,
      body: {},
    },
  );
}

export function generateCommitteeMeetingPack(
  token: string,
  committeeId: string,
  request: GenerateCommitteeMeetingPackRequest = {},
): Promise<GeneratedReportRead> {
  return apiRequest<GeneratedReportRead>(
    `/reports/committee-meeting-packs/${encodeURIComponent(committeeId)}`,
    {
      method: "POST",
      token,
      body: request,
    },
  );
}

export async function listGeneratedReports(
  token: string,
  params: GeneratedReportListParams = {},
): Promise<GeneratedReportRead[]> {
  const query = new URLSearchParams();

  if (params.riskRecordId) {
    query.set("risk_record_id", params.riskRecordId);
  }

  if (params.reportType) {
    query.set("report_type", params.reportType);
  }

  const queryString = query.toString();
  const path = queryString ? `/reports?${queryString}` : "/reports";
  const response = await apiRequest<GeneratedReportListResponse>(path, {
    token,
  });

  return Array.isArray(response) ? response : response.items ?? [];
}

export async function downloadGeneratedReport(
  token: string,
  generatedReportId: string,
): Promise<{ blob: Blob; filename: string }> {
  const url = `${API_BASE_URL}/reports/${encodeURIComponent(
    generatedReportId,
  )}/download`;

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
    let message = "Unable to download report.";
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
      // Keep the default message if the error body cannot be parsed.
    }

    throw new ApiError(
      message,
      response.status,
      "REPORT_DOWNLOAD_ERROR",
      details,
    );
  }

  const blob = await response.blob();
  const filename =
    getFilenameFromContentDisposition(
      response.headers.get("content-disposition"),
    ) ?? `risk-report-${generatedReportId}.docx`;

  return { blob, filename };
}

export function saveBlobAsFile(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
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
