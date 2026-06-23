import { API_BASE_URL } from "../config/env";
import type { StandardApiError } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
    public readonly details: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiRequestOptions extends Omit<RequestInit, "body" | "headers"> {
  body?: unknown;
  headers?: HeadersInit;
  token?: string;
}

function isStandardApiError(value: unknown): value is StandardApiError {
  if (!value || typeof value !== "object" || !("error" in value)) {
    return false;
  }

  const error = value.error;
  return (
    !!error &&
    typeof error === "object" &&
    "code" in error &&
    typeof error.code === "string" &&
    "message" in error &&
    typeof error.message === "string"
  );
}

function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  return contentType.includes("application/json")
    ? response.json()
    : response.text();
}

export async function apiRequest<T>(
  path: string,
  { body, headers, token, ...options }: ApiRequestOptions = {},
): Promise<T> {
  const requestHeaders = new Headers(headers);
  const hasJsonBody = body !== undefined && !(body instanceof FormData);

  if (hasJsonBody && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (token) {
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    const url = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
    response = await fetch(url, {
      ...options,
      headers: requestHeaders,
      body: hasJsonBody ? JSON.stringify(body) : body,
    });
  } catch {
    throw new ApiError("Unable to reach the API.", 0, "NETWORK_ERROR", {});
  }

  const responseBody = await parseResponseBody(response);

  if (!response.ok) {
    if (isStandardApiError(responseBody)) {
      throw new ApiError(
        responseBody.error.message,
        response.status,
        responseBody.error.code,
        responseBody.error.details,
      );
    }

    throw new ApiError(
      "The API request failed.",
      response.status,
      "HTTP_ERROR",
      responseBody,
    );
  }

  return responseBody as T;
}
