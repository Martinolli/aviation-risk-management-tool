export interface StandardApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

export interface UserRead {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
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
