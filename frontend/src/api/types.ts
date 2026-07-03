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
  created_at?: string;
  updated_at?: string;
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

export type AuditAction =
  | "CREATE"
  | "UPDATE"
  | "DELETE"
  | "WORKFLOW"
  | "LOGIN"
  | "GENERATE_REPORT"
  | string;

export interface AuditLogRead {
  id: string;
  entity_type: string;
  entity_id: string;
  action: AuditAction;
  field_name?: string | null;
  old_value?: unknown;
  new_value?: unknown;
  changed_by_user_id?: string | null;
  changed_at: string;
  reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiskRecordRead {
  id: string;
  risk_id: string | null;
  problem_description: string;
  source_trigger: string | null;
  domain: string;
  board_of_origin_id?: string | null;
  system_scope?: string | null;
  central_event?: string | null;
  hazard_statement?: string | null;
  causes?: string[] | null;
  consequences?: string[] | null;
  existing_controls?: string[] | null;
  workflow_status: string;
  lifecycle_status: string;
  owner_user_id: string | null;
  created_by_user_id: string | null;
  is_active?: boolean;
  archived_at?: string | null;
  archive_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RiskCreateRequest {
  problem_description: string;
  domain: string;
  source_trigger?: string | null;
  board_of_origin_id?: string | null;
}

export interface RiskUpdateRequest {
  source_trigger?: string | null;
  domain?: string | null;
  board_of_origin_id?: string | null;
  system_scope?: string | null;
  central_event?: string | null;
  hazard_statement?: string | null;
  causes?: string[] | null;
  consequences?: string[] | null;
  existing_controls?: string[] | null;
  owner_user_id?: string | null;
}

export interface RiskSubmitRequest {
  reason?: string | null;
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
  risk_record_id?: string | null;
  title?: string | null;
  description?: string | null;
  action_owner_user_id?: string | null;
  due_date?: string | null;
  status?: string | null;
  completion_notes?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RiskActionCreateRequest {
  risk_record_id: string;
  title: string;
  description?: string | null;
  action_owner_user_id?: string | null;
  due_date?: string | null;
}

export interface RiskActionCompleteRequest {
  completion_notes?: string | null;
}

export interface RiskEvidenceRead {
  id: string;
  risk_record_id: string;
  original_filename: string;
  content_type?: string | null;
  file_size_bytes: number;
  description?: string | null;
  uploaded_by_user_id?: string | null;
  uploaded_at: string;
  is_active: boolean;
  archived_at?: string | null;
  archived_by_user_id?: string | null;
  archive_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RiskEvidenceArchiveRequest {
  archive_reason?: string | null;
}

export type RiskMonitoringStatus =
  | "ACTIVE"
  | "DUE"
  | "OVERDUE"
  | "CLOSED"
  | "CANCELLED"
  | string;

export type RiskMonitoringReviewOutcome =
  | "CONTINUE_MONITORING"
  | "EFFECTIVE_CONTROLS"
  | "CONTROLS_NOT_EFFECTIVE"
  | "REASSESSMENT_REQUIRED"
  | "ESCALATION_RECOMMENDED"
  | "CLOSE_MONITORING"
  | string;

export interface RiskMonitoringReviewRead {
  id: string;
  risk_record_id: string;
  monitoring_owner_user_id?: string | null;
  review_frequency?: string | null;
  next_review_date?: string | null;
  last_reviewed_at?: string | null;
  status: RiskMonitoringStatus;
  review_notes?: string | null;
  effectiveness_review?: string | null;
  review_outcome?: RiskMonitoringReviewOutcome | null;
  reviewed_by_user_id?: string | null;
  created_by_user_id?: string | null;
  closed_at?: string | null;
  closed_by_user_id?: string | null;
  closure_reason?: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CommitteeRead {
  id: string;
  name: string;
  description?: string | null;
  authority_level: "LOW" | "MIDDLE" | "HIGH" | string;
  committee_type: string;
  is_fixed: boolean;
  is_active: boolean;
  archived_at?: string | null;
  archive_reason?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CommitteeMemberRead {
  id: string;
  committee_id: string;
  user_id: string;
  role_label?: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface MyDecisionQueueCommitteeRead {
  committee_id: string;
  committee_name: string;
  authority_level: string;
  committee_type: string;
  role_label?: string | null;
  queue_scope: string | string[];
  is_active: boolean;
}

export interface MyDecisionQueueItemRead {
  risk_record: RiskRecordRead;
  committee_id: string;
  committee_name: string;
  authority_level: string;
  role_label?: string | null;
  queue_reason: string;
}

export interface MyDecisionQueueRead {
  user_id: string;
  committees: MyDecisionQueueCommitteeRead[];
  queue_items: MyDecisionQueueItemRead[];
}

export type RiskDecisionType =
  | "APPROVE"
  | "REJECT"
  | "ESCALATE"
  | "RETURN_FOR_REVISION"
  | "ACCEPT_RESIDUAL_RISK"
  | "CLOSE";

export interface RiskDecisionCreateRequest {
  risk_record_id: string;
  committee_id: string;
  decision_type: RiskDecisionType;
  decision_text: string;
}

export interface RiskDecisionRead {
  id: string;
  risk_record_id?: string | null;
  committee_id?: string | null;
  decision_type?: string | null;
  decision_text?: string | null;
  decided_by_user_id?: string | null;
  decided_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface GeneratedReportRead {
  id: string;
  risk_record_id?: string | null;
  committee_id?: string | null;
  report_type: string;
  file_path: string;
  generated_by_user_id?: string | null;
  generated_at: string;
  created_at: string;
  updated_at: string;
}

export interface GenerateRiskDossierReportRequest {
  output_dir?: string | null;
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
  monitoring_reviews: RiskMonitoringReviewRead[];
  audit_summary?: RiskAuditSummary;
}
