import type { RiskAssessmentRead, RiskRecordRead } from "../api/types";

export interface RiskReadinessCheck {
  key: string;
  label: string;
  isComplete: boolean;
  actionTo?: string;
  actionLabel?: string;
}

export interface RiskSubmissionReadiness {
  isReady: boolean;
  missingItems: string[];
  checks: RiskReadinessCheck[];
  packageMinimumComplete: boolean;
  hasInitialAssessment: boolean;
  hasBoardOfOrigin: boolean;
}

export type RiskPackageStatusTone =
  | "neutral"
  | "warning"
  | "success"
  | "info";

export function getRiskSubmissionReadiness(
  risk: RiskRecordRead,
  assessments?: RiskAssessmentRead[],
): RiskSubmissionReadiness {
  const packageEditAction = {
    actionTo: `/risks/${risk.id}/package/edit`,
    actionLabel: "Complete risk package",
  };
  const hasBoardOfOrigin = Boolean(risk.board_of_origin_id);
  const hasInitialAssessment = Boolean(
    assessments?.some(
      (assessment) => assessment.assessment_type === "INITIAL",
    ),
  );
  const checks: RiskReadinessCheck[] = [
    {
      key: "board_of_origin",
      label: "Board of Origin / Originating Committee",
      isComplete: hasBoardOfOrigin,
    },
    {
      key: "system_scope",
      label: "System Scope",
      isComplete: Boolean(risk.system_scope?.trim()),
      ...packageEditAction,
    },
    {
      key: "central_event",
      label: "Central Event",
      isComplete: Boolean(risk.central_event?.trim()),
      ...packageEditAction,
    },
    {
      key: "hazard_statement",
      label: "Hazard Statement",
      isComplete: Boolean(risk.hazard_statement?.trim()),
      ...packageEditAction,
    },
    {
      key: "initial_assessment",
      label: "Initial Risk Assessment",
      isComplete: hasInitialAssessment,
      actionTo: `/risks/${risk.id}/assessments/initial/new`,
      actionLabel: "Add initial assessment",
    },
  ];
  const packageMinimumComplete = checks
    .filter((check) =>
      ["system_scope", "central_event", "hazard_statement"].includes(
        check.key,
      ),
    )
    .every((check) => check.isComplete);
  const missingItems = checks
    .filter((check) => !check.isComplete)
    .map((check) => check.label);

  return {
    isReady: missingItems.length === 0,
    missingItems,
    checks,
    packageMinimumComplete,
    hasInitialAssessment,
    hasBoardOfOrigin,
  };
}

export function getRiskPackageStatusLabel(
  risk: RiskRecordRead,
  assessments?: RiskAssessmentRead[],
): string {
  if (risk.workflow_status !== "DRAFT") {
    if (
      risk.workflow_status === "CLOSED" ||
      risk.lifecycle_status === "CLOSED"
    ) {
      return "Closed";
    }
    return formatWorkflowStatus(risk.workflow_status);
  }

  const readiness = getRiskSubmissionReadiness(risk, assessments);
  if (!readiness.hasBoardOfOrigin || !readiness.packageMinimumComplete) {
    return "Draft incomplete";
  }
  if (assessments && readiness.hasInitialAssessment) {
    return "Ready to submit";
  }
  return "Package complete";
}

export function getRiskPackageStatusTone(
  risk: RiskRecordRead,
  assessments?: RiskAssessmentRead[],
): RiskPackageStatusTone {
  if (risk.workflow_status !== "DRAFT") {
    return risk.workflow_status === "CLOSED" || risk.lifecycle_status === "CLOSED"
      ? "neutral"
      : "info";
  }

  const readiness = getRiskSubmissionReadiness(risk, assessments);
  if (!readiness.hasBoardOfOrigin || !readiness.packageMinimumComplete) {
    return "warning";
  }
  if (assessments && readiness.hasInitialAssessment) {
    return "success";
  }
  return "info";
}

function formatWorkflowStatus(status: string): string {
  return status
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
