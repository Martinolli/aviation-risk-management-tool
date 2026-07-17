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

export interface UserCreateRequest {
  email: string;
  display_name: string;
  password?: string | null;
}

export interface UserUpdateRequest {
  display_name?: string | null;
  is_active?: boolean | null;
  password?: string | null;
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

export interface CommitteeCreateRequest {
  name: string;
  description?: string | null;
  authority_level: "LOW" | "MIDDLE" | "HIGH" | string;
  committee_type: string;
}

export interface CommitteeUpdateRequest {
  name?: string | null;
  description?: string | null;
  is_active?: boolean | null;
}

export interface CommitteeArchiveRequest {
  archive_reason: string;
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

export interface CommitteeMemberCreateRequest {
  committee_id: string;
  user_id: string;
  role_label?: string | null;
}

export interface CommitteeMemberUpdateRequest {
  role_label?: string | null;
  is_active?: boolean | null;
}

export type CommitteeMeetingStatus = "DRAFT" | "FINALIZED" | "CANCELLED";

export type CommitteeMeetingAttendanceStatus =
  | "PRESENT"
  | "ABSENT"
  | "APOLOGY"
  | "OBSERVER";

export interface CommitteeMeetingAttendeeRead {
  id: string;
  meeting_id: string;
  user_id?: string | null;
  attendee_name?: string | null;
  attendee_email?: string | null;
  role_label?: string | null;
  attendance_status: CommitteeMeetingAttendanceStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CommitteeMeetingRiskItemRead {
  id: string;
  meeting_id: string;
  risk_record_id: string;
  agenda_item_number?: number | null;
  discussion_summary?: string | null;
  decision_summary?: string | null;
  action_items?: string | null;
  linked_risk_decision_id?: string | null;
  follow_up_required: boolean;
  follow_up_notes?: string | null;
  risk_id?: string | null;
  risk_problem_description?: string | null;
  risk_domain?: string | null;
  risk_workflow_status?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CommitteeMeetingRead {
  id: string;
  committee_id: string;
  title: string;
  meeting_date: string;
  meeting_time_utc?: string | null;
  location?: string | null;
  chair_user_id?: string | null;
  created_by_user_id?: string | null;
  status: CommitteeMeetingStatus;
  agenda_summary?: string | null;
  discussion_summary?: string | null;
  decisions_summary?: string | null;
  action_items_summary?: string | null;
  finalized_at?: string | null;
  finalized_by_user_id?: string | null;
  cancellation_reason?: string | null;
  is_active: boolean;
  committee_name?: string | null;
  authority_level?: string | null;
  committee_type?: string | null;
  attendees: CommitteeMeetingAttendeeRead[];
  risk_items: CommitteeMeetingRiskItemRead[];
  created_at: string;
  updated_at: string;
}

export interface CommitteeMeetingAttendeeCreateRequest {
  user_id?: string | null;
  attendee_name?: string | null;
  attendee_email?: string | null;
  role_label?: string | null;
  attendance_status?: CommitteeMeetingAttendanceStatus;
  notes?: string | null;
}

export interface CommitteeMeetingRiskItemCreateRequest {
  risk_record_id: string;
  agenda_item_number?: number | null;
  discussion_summary?: string | null;
  decision_summary?: string | null;
  action_items?: string | null;
  linked_risk_decision_id?: string | null;
  follow_up_required?: boolean;
  follow_up_notes?: string | null;
}

export interface CommitteeMeetingRiskItemUpdateRequest {
  agenda_item_number?: number | null;
  discussion_summary?: string | null;
  decision_summary?: string | null;
  action_items?: string | null;
  linked_risk_decision_id?: string | null;
  follow_up_required?: boolean | null;
  follow_up_notes?: string | null;
}

export interface CommitteeMeetingCreateRequest {
  committee_id: string;
  title: string;
  meeting_date: string;
  meeting_time_utc?: string | null;
  location?: string | null;
  chair_user_id?: string | null;
  agenda_summary?: string | null;
  discussion_summary?: string | null;
  decisions_summary?: string | null;
  action_items_summary?: string | null;
  attendees?: CommitteeMeetingAttendeeCreateRequest[];
  risk_items?: CommitteeMeetingRiskItemCreateRequest[];
}

export interface CommitteeMeetingUpdateRequest {
  title?: string;
  meeting_date?: string;
  meeting_time_utc?: string | null;
  location?: string | null;
  chair_user_id?: string | null;
  agenda_summary?: string | null;
  discussion_summary?: string | null;
  decisions_summary?: string | null;
  action_items_summary?: string | null;
}

export interface CommitteeMeetingFinalizeRequest {
  finalization_notes?: string | null;
}

export interface CommitteeMeetingCancelRequest {
  cancellation_reason?: string | null;
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

export type NotificationSeverity = "CRITICAL" | "WARNING" | "INFO";

export type NotificationCategory =
  | "ACTION"
  | "MONITORING"
  | "DECISION_QUEUE"
  | "MEETING";

export interface NotificationRead {
  id: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  title: string;
  message: string;
  target_type: string;
  target_id: string;
  risk_record_id?: string | null;
  risk_id?: string | null;
  committee_id?: string | null;
  committee_name?: string | null;
  due_date?: string | null;
  created_reference_at?: string | null;
  action_url?: string | null;
}

export interface NotificationSummaryRead {
  total_count: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  action_count: number;
  monitoring_count: number;
  decision_queue_count: number;
  meeting_count: number;
  items: NotificationRead[];
}

export interface ManagementDashboardKpi {
  key: string;
  label: string;
  value: number;
  detail?: string | null;
  severity?: string | null;
}

export interface ManagementDashboardRiskSummary {
  risk_record_id: string;
  risk_id?: string | null;
  problem_description: string;
  domain: string;
  workflow_status: string;
  lifecycle_status: string;
  latest_risk_level?: string | null;
  board_of_origin_id?: string | null;
  board_of_origin_name?: string | null;
  owner_user_id?: string | null;
  updated_at?: string | null;
}

export interface ManagementDashboardGroup {
  key: string;
  label: string;
  count: number;
}

export interface ManagementDashboardAttentionItem {
  category: string;
  severity: string;
  title: string;
  message: string;
  target_type: string;
  target_id: string;
  risk_record_id?: string | null;
  risk_id?: string | null;
  action_url?: string | null;
  due_date?: string | null;
}

export interface ManagementDashboardRead {
  generated_at: string;
  kpis: ManagementDashboardKpi[];
  risk_level_distribution: ManagementDashboardGroup[];
  domain_hotspots: ManagementDashboardGroup[];
  workflow_backlog: ManagementDashboardGroup[];
  authority_level_backlog: ManagementDashboardGroup[];
  top_attention_items: ManagementDashboardAttentionItem[];
  high_exposure_risks: ManagementDashboardRiskSummary[];
  overdue_action_risks: ManagementDashboardRiskSummary[];
  monitoring_concern_risks: ManagementDashboardRiskSummary[];
  committee_backlog_risks: ManagementDashboardRiskSummary[];
}

export interface DataRetentionPolicyItemRead {
  record_type: string;
  description: string;
  default_retention_period: string;
  archive_rule: string;
  deletion_rule: string;
  owner: string;
  notes: string;
}

export interface DataRetentionPolicyRead {
  policy_name: string;
  policy_version: string;
  effective_status: string;
  generated_at: string;
  summary: string;
  principles: string[];
  items: DataRetentionPolicyItemRead[];
  no_hard_delete_record_types: string[];
  requires_legal_or_investigation_hold_review: string[];
}

export interface PermissionMatrixRuleRead {
  area: string;
  capability: string;
  allowed_roles_or_users: string[];
  authority_level?: string | null;
  access_basis: string;
  restrictions: string;
  audit_expected: boolean;
  notes?: string | null;
}

export interface PermissionMatrixSectionRead {
  section: string;
  description: string;
  rules: PermissionMatrixRuleRead[];
}

export interface PermissionMatrixRead {
  policy_name: string;
  policy_version: string;
  effective_status: string;
  generated_at: string;
  summary: string;
  principles: string[];
  sections: PermissionMatrixSectionRead[];
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

export type ElectronicApprovalTargetType =
  | "RISK_RECORD"
  | "RISK_DECISION"
  | "COMMITTEE_MEETING"
  | "GENERATED_REPORT";

export interface ElectronicApprovalCreateRequest {
  target_type: ElectronicApprovalTargetType;
  target_id: string;
  approval_statement: string;
  acknowledgement_text?: string | null;
}

export interface ElectronicApprovalRead {
  id: string;
  target_type: ElectronicApprovalTargetType;
  target_id: string;
  risk_record_id?: string | null;
  risk_decision_id?: string | null;
  committee_id?: string | null;
  authority_level?: string | null;
  approved_by_user_id: string;
  approved_at: string;
  approval_statement: string;
  acknowledgement_text: string;
  meaning_of_signature: string;
  status: string;
  approval_hash: string;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
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
