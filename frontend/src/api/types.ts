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
  risk_record_id?: string | null;
  assessment_type?: string | null;
  severity?: string | null;
  likelihood?: string | null;
  risk_level?: string | null;
  rationale?: string | null;
  assessed_by_user_id?: string | null;
  assessed_at?: string | null;
  severity_level_id?: string | null;
  likelihood_level_id?: string | null;
  calculated_risk_level_id?: string | null;
  matrix_cell_id?: string | null;
  calculated_score?: number | null;
  is_tolerable?: boolean | null;
  requires_mitigation?: boolean | null;
  requires_escalation?: boolean | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RiskAssessmentCreateRequest {
  risk_record_id: string;
  assessment_type: "INITIAL" | "RESIDUAL";
  rationale?: string | null;
  severity_level_id?: string | null;
  likelihood_level_id?: string | null;
}

export interface RiskMatrixReferenceRead {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  numeric_value: number;
  is_active: boolean;
  archived_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type RiskSeverityLevelRead = RiskMatrixReferenceRead;
export type RiskLikelihoodLevelRead = RiskMatrixReferenceRead;

export interface RiskLevelRead extends RiskMatrixReferenceRead {
  color?: string | null;
  is_tolerable: boolean;
  requires_mitigation: boolean;
  requires_escalation: boolean;
}

export interface RiskMatrixCellRead {
  id: string;
  severity_level_id: string;
  likelihood_level_id: string;
  risk_level_id: string;
  score?: number | null;
  label?: string | null;
  is_active: boolean;
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
