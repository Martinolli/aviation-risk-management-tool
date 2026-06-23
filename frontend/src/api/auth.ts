import { apiRequest } from "./client";
import type { LoginRequest, LoginResponse, UserRead } from "./types";

export function login(request: LoginRequest): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: request,
  });
}

export function getCurrentUser(token: string): Promise<UserRead> {
  return apiRequest<UserRead>("/auth/me", { token });
}
