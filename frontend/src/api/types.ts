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

export interface RiskCreateRequest {
  problem_description: string;
  domain: string;
  source_trigger?: string | null;
}

export interface RiskAssessmentRead {
  id: string;
  assessment_type?: string | null;
  severity?: string | null;
  likelihood?: string | null;
  risk_level?: string | null;
  calculated_score?: number | null;
  is_tolerable?: boolean | null;
  requires_mitigation?: boolean | null;
  requires_escalation?: boolean | null;
  created_at?: string | null;
}

export interface RiskActionRead {
  id: string;
  title?: string | null;
  description?: string | null;
  status?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
}

export interface RiskDecisionRead {
  id: string;
  decision_type?: string | null;
  decision_text?: string | null;
  created_at?: string | null;
}

export interface RiskAuditSummary {
  total_count?: number;
  create_count?: number;
  update_count?: number;
  workflow_count?: number;
  latest_changed_at?: string | null;
}

export interface RiskDetailResponse {
  risk_record?: RiskRecordRead;
  risk?: RiskRecordRead;
  record?: RiskRecordRead;
  assessments?: RiskAssessmentRead[];
  actions?: RiskActionRead[];
  decisions?: RiskDecisionRead[];
  audit_summary?: RiskAuditSummary;
}
