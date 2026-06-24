export interface StandardApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

export interface HealthResponse {
  status: string;
  service: string;
}

export interface UserRead {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserRead;
}

export interface RiskRecordRead {
  id: string;
  risk_id: string | null;
  problem_description: string;
  source_trigger: string | null;
  domain: string;
  workflow_status: string;
  lifecycle_status: string;
  owner_user_id: string | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}
