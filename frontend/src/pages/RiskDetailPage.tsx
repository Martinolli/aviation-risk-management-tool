import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useParams } from "react-router-dom";

import { listAuditLogs } from "../api/auditLogs";
import { ApiError } from "../api/client";
import { listCommittees } from "../api/committees";
import {
  downloadGeneratedReport,
  generateRiskDossierReport,
  generateRiskEvidencePackage,
  listGeneratedReports,
  saveBlobAsFile,
} from "../api/reports";
import { getRiskDetail } from "../api/risks";
import {
  archiveRiskEvidence,
  downloadRiskEvidence,
  listRiskEvidence,
  uploadRiskEvidence,
} from "../api/riskEvidence";
import {
  closeRiskMonitoringReview,
  completeRiskMonitoringReview,
  createRiskMonitoringReview,
  listRiskMonitoringReviews,
  type RiskMonitoringReviewCompleteRequest,
} from "../api/riskMonitoring";
import type {
  AuditLogRead,
  CommitteeRead,
  GeneratedReportRead,
  RiskActionRead,
  RiskAssessmentRead,
  RiskDecisionRead,
  RiskDetailResponse,
  RiskEvidenceRead,
  RiskMonitoringReviewRead,
  RiskMonitoringReviewOutcome,
  RiskRecordRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AuditLogList } from "../components/AuditLogList";
import {
  getRiskPackageStatusLabel,
  getRiskSubmissionReadiness,
} from "../utils/riskReadiness";
import {
  getRiskActionDueStatus,
  getRiskActionDueStatusLabel,
  getRiskActionDueStatusTone,
  isRiskActionOpen,
} from "../utils/actionDueStatus";

type RiskDetailState =
  | { status: "loading" }
  | { status: "success"; detail: RiskDetailResponse }
  | { status: "error"; message: string };

type RiskReportsState =
  | { status: "idle" | "loading" }
  | { status: "success"; reports: GeneratedReportRead[] }
  | { status: "error"; message: string };

type RiskEvidenceState =
  | { status: "idle" | "loading" }
  | { status: "success"; evidenceItems: RiskEvidenceRead[] }
  | { status: "error"; message: string };

type RiskMonitoringState =
  | { status: "idle" | "loading" }
  | { status: "success"; monitoringReviews: RiskMonitoringReviewRead[] }
  | { status: "error"; message: string };

type RiskAuditTrailState =
  | { status: "idle" | "loading" }
  | { status: "success"; auditLogs: AuditLogRead[] }
  | { status: "error"; message: string };

interface RiskAuditTrailResult {
  auditLogs: AuditLogRead[];
  failedScopeCount: number;
}

type RiskCommitteesState =
  | { status: "loading" }
  | { status: "success"; committees: CommitteeRead[] }
  | { status: "error" };

interface NextAction {
  title: string;
  description: string;
  linkLabel?: string;
  linkTo?: string;
  statusTone: "info" | "warning" | "success" | "blocked";
  checklist: string[];
}

export function RiskDetailPage() {
  const { isAuthenticated, token, user } = useAuth();
  const { riskRecordId } = useParams();
  const location = useLocation();
  const [riskDetail, setRiskDetail] = useState<RiskDetailState>({
    status: "loading",
  });
  const [riskReports, setRiskReports] = useState<RiskReportsState>({
    status: "idle",
  });
  const [riskEvidence, setRiskEvidence] = useState<RiskEvidenceState>({
    status: "idle",
  });
  const [riskMonitoring, setRiskMonitoring] = useState<RiskMonitoringState>({
    status: "idle",
  });
  const [riskAuditTrail, setRiskAuditTrail] = useState<RiskAuditTrailState>({
    status: "idle",
  });
  const [riskAuditWarning, setRiskAuditWarning] = useState<string | null>(null);
  const [riskCommittees, setRiskCommittees] = useState<RiskCommitteesState>({
    status: "loading",
  });
  const [reportMessage, setReportMessage] = useState<string | null>(null);
  const [reportErrorMessage, setReportErrorMessage] = useState<string | null>(
    null,
  );
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [downloadingReportId, setDownloadingReportId] = useState<string | null>(
    null,
  );
  const [includeArchivedEvidence, setIncludeArchivedEvidence] = useState(false);
  const [includeRiskDossier, setIncludeRiskDossier] = useState(true);
  const [evidencePackageReport, setEvidencePackageReport] =
    useState<GeneratedReportRead | null>(null);
  const [evidencePackageError, setEvidencePackageError] = useState<string | null>(
    null,
  );
  const [isGeneratingEvidencePackage, setIsGeneratingEvidencePackage] =
    useState(false);
  const [isDownloadingEvidencePackage, setIsDownloadingEvidencePackage] =
    useState(false);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceDescription, setEvidenceDescription] = useState("");
  const [evidenceMessage, setEvidenceMessage] = useState<string | null>(null);
  const [evidenceErrorMessage, setEvidenceErrorMessage] = useState<string | null>(
    null,
  );
  const [isUploadingEvidence, setIsUploadingEvidence] = useState(false);
  const [downloadingEvidenceId, setDownloadingEvidenceId] = useState<
    string | null
  >(null);
  const [archivingEvidenceId, setArchivingEvidenceId] = useState<string | null>(
    null,
  );
  const [monitoringOwnerUserId, setMonitoringOwnerUserId] = useState("");
  const [monitoringFrequency, setMonitoringFrequency] = useState("");
  const [monitoringNextReviewDate, setMonitoringNextReviewDate] = useState("");
  const [monitoringNotes, setMonitoringNotes] = useState("");
  const [monitoringEffectivenessReview, setMonitoringEffectivenessReview] =
    useState("");
  const [monitoringMessage, setMonitoringMessage] = useState<string | null>(null);
  const [monitoringErrorMessage, setMonitoringErrorMessage] = useState<
    string | null
  >(null);
  const [isCreatingMonitoring, setIsCreatingMonitoring] = useState(false);
  const [completingMonitoringId, setCompletingMonitoringId] = useState<
    string | null
  >(null);
  const [closingMonitoringId, setClosingMonitoringId] = useState<string | null>(
    null,
  );

  useEffect(() => {
    let isCurrent = true;

    if (!token || !riskRecordId) {
      return;
    }

    const tokenToUse = token;
    const idToLoad = riskRecordId;

    async function loadRiskDetail() {
      try {
        if (isCurrent) {
          setRiskDetail({ status: "loading" });
          setRiskReports({ status: "loading" });
          setRiskEvidence({ status: "loading" });
          setRiskMonitoring({ status: "loading" });
          setRiskAuditTrail({ status: "loading" });
          setRiskAuditWarning(null);
          setReportMessage(null);
          setReportErrorMessage(null);
          setEvidencePackageReport(null);
          setEvidencePackageError(null);
        }

        const detail = await getRiskDetail(tokenToUse, idToLoad);
        if (isCurrent) {
          setRiskDetail({ status: "success", detail });
          setRiskMonitoring({
            status: "success",
            monitoringReviews: detail.monitoring_reviews ?? [],
          });
        }

        const risk = getRiskRecord(detail);
        if (!risk) {
          if (isCurrent) {
            setRiskReports({ status: "idle" });
            setRiskEvidence({ status: "idle" });
            setRiskMonitoring({ status: "idle" });
            setRiskAuditTrail({ status: "idle" });
          }
          return;
        }

        try {
          const evidenceItems = await listRiskEvidence(tokenToUse, risk.id);
          if (isCurrent) {
            setRiskEvidence({ status: "success", evidenceItems });
          }
        } catch (error) {
          if (isCurrent) {
            setRiskEvidence({
              status: "error",
              message:
                error instanceof ApiError
                  ? error.message
                  : "Please try again shortly.",
            });
          }
        }

        let reports: GeneratedReportRead[] = [];
        try {
          reports = await listGeneratedReports(tokenToUse, {
            riskRecordId: risk.id,
          });
          if (isCurrent) {
            setRiskReports({ status: "success", reports });
          }
        } catch (error) {
          if (isCurrent) {
            setRiskReports({
              status: "error",
              message:
                error instanceof ApiError
                  ? error.message
                  : "Please try again shortly.",
            });
          }
        }

        try {
          const result = await loadRiskAuditTrail({
            token: tokenToUse,
            risk,
            assessments: detail.assessments ?? [],
            actions: detail.actions ?? [],
            decisions: detail.decisions ?? [],
            monitoringReviews: detail.monitoring_reviews ?? [],
            reports,
          });
          if (isCurrent) {
            setRiskAuditTrail({
              status: "success",
              auditLogs: result.auditLogs,
            });
            setRiskAuditWarning(
              result.failedScopeCount > 0
                ? "Some related audit scopes could not be loaded. Showing the authorized records that are available."
                : null,
            );
          }
        } catch (error) {
          if (isCurrent) {
            setRiskAuditTrail({
              status: "error",
              message:
                error instanceof ApiError
                  ? error.message
                  : "No related audit scopes could be loaded.",
            });
            setRiskAuditWarning(null);
          }
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setRiskDetail({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
        setRiskReports({ status: "idle" });
        setRiskEvidence({ status: "idle" });
        setRiskMonitoring({ status: "idle" });
        setRiskAuditTrail({ status: "idle" });
        setRiskAuditWarning(null);
      }
    }

    void loadRiskDetail();

    return () => {
      isCurrent = false;
    };
  }, [riskRecordId, token]);

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadCommitteeDetails() {
      setRiskCommittees({ status: "loading" });
      try {
        const committees = await listCommittees(tokenToUse);
        if (isCurrent) {
          setRiskCommittees({ status: "success", committees });
        }
      } catch {
        if (isCurrent) {
          setRiskCommittees({ status: "error" });
        }
      }
    }

    void loadCommitteeDetails();

    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (!riskRecordId) {
    return <Navigate replace to="/risks" />;
  }

  if (riskDetail.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading risk detail...
      </p>
    );
  }

  if (riskDetail.status === "error") {
    return (
      <section className="risk-detail-page" aria-labelledby="risk-detail-error">
        <Link className="back-link" to="/risks">
          Back to risk records
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="risk-detail-error">Unable to load risk detail.</strong>
          <span>{riskDetail.message}</span>
        </div>
      </section>
    );
  }

  const risk = getRiskRecord(riskDetail.detail);

  if (!risk) {
    return (
      <section className="risk-detail-page" aria-labelledby="risk-detail-error">
        <Link className="back-link" to="/risks">
          Back to risk records
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="risk-detail-error">Unable to load risk detail.</strong>
          <span>The API response did not include a risk record.</span>
        </div>
      </section>
    );
  }

  const assessments = riskDetail.detail.assessments ?? [];
  const loadedRiskId = risk.id;
  const actions = riskDetail.detail.actions ?? [];
  const decisions = riskDetail.detail.decisions ?? [];
  const boardOfOrigin =
    risk.board_of_origin_id && riskCommittees.status === "success"
      ? riskCommittees.committees.find(
          (committee) => committee.id === risk.board_of_origin_id,
        )
      : undefined;
  const submissionReadiness = getRiskSubmissionReadiness(risk, assessments);
  const initialAssessmentExists = submissionReadiness.hasInitialAssessment;
  const initialAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const residualAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "RESIDUAL",
  );
  const canEditRiskPackage = canUserUpdateRiskPackage(risk, user?.id);
  const hasRiskPackageContent = hasAnyRiskPackageContent(risk);
  const nextAction = getNextAction({
    risk,
    assessments,
    actions,
    decisions,
    canEditRiskPackage,
  });
  const allActionsCompleted =
    actions.length > 0 && actions.every((action) => isActionCompleted(action));
  const actionDueStatuses = actions.map((action) =>
    getRiskActionDueStatus(action),
  );
  const hasOverdueActions = actionDueStatuses.includes("OVERDUE");
  const hasActionsDueToday = actionDueStatuses.includes("DUE_TODAY");
  const successMessage = getSuccessMessage(location.state);

  async function refreshRiskReports(riskId: string) {
    if (!token) {
      return;
    }

    setRiskReports({ status: "loading" });

    try {
      const reports = await listGeneratedReports(token, { riskRecordId: riskId });
      setRiskReports({ status: "success", reports });
    } catch (error) {
      setRiskReports({
        status: "error",
        message:
          error instanceof ApiError
            ? error.message
            : "Please try again shortly.",
      });
    }
  }

  async function handleGenerateReport() {
    if (!token) {
      return;
    }

    const riskToUse = risk;
    if (!riskToUse) {
      return;
    }

    setIsGeneratingReport(true);
    setReportMessage(null);
    setReportErrorMessage(null);

    try {
      await generateRiskDossierReport(token, riskToUse.id);
      setReportMessage("Risk dossier report generated.");
      await refreshRiskReports(riskToUse.id);
    } catch (error) {
      setReportErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to generate risk dossier report.",
      );
    } finally {
      setIsGeneratingReport(false);
    }
  }

  async function handleDownloadReport(report: GeneratedReportRead) {
    if (!token) {
      return;
    }

    setDownloadingReportId(report.id);
    setReportErrorMessage(null);

    try {
      const { blob, filename } = await downloadGeneratedReport(token, report.id);
      saveBlobAsFile(blob, filename);
    } catch (error) {
      setReportErrorMessage(
        error instanceof ApiError ? error.message : "Unable to download report.",
      );
    } finally {
      setDownloadingReportId(null);
    }
  }

  async function handleGenerateEvidencePackage() {
    if (!token) {
      return;
    }

    setIsGeneratingEvidencePackage(true);
    setEvidencePackageError(null);
    setEvidencePackageReport(null);
    try {
      const report = await generateRiskEvidencePackage(token, loadedRiskId, {
        include_archived: includeArchivedEvidence,
        include_risk_dossier: includeRiskDossier,
      });
      setEvidencePackageReport(report);
      await refreshRiskReports(loadedRiskId);
    } catch (error) {
      setEvidencePackageError(
        error instanceof ApiError
          ? error.message
          : "Unable to generate Risk Evidence Package.",
      );
    } finally {
      setIsGeneratingEvidencePackage(false);
    }
  }

  async function handleDownloadEvidencePackage() {
    if (!token || !evidencePackageReport) {
      return;
    }

    setIsDownloadingEvidencePackage(true);
    setEvidencePackageError(null);
    try {
      const { blob, filename } = await downloadGeneratedReport(
        token,
        evidencePackageReport.id,
      );
      saveBlobAsFile(blob, filename);
    } catch (error) {
      setEvidencePackageError(
        error instanceof ApiError
          ? error.message
          : "Unable to download Risk Evidence Package.",
      );
    } finally {
      setIsDownloadingEvidencePackage(false);
    }
  }

  async function refreshRiskEvidence(riskId: string) {
    if (!token) {
      return;
    }
    setRiskEvidence({ status: "loading" });
    try {
      const evidenceItems = await listRiskEvidence(token, riskId);
      setRiskEvidence({ status: "success", evidenceItems });
    } catch (error) {
      setRiskEvidence({
        status: "error",
        message:
          error instanceof ApiError ? error.message : "Please try again shortly.",
      });
    }
  }

  async function handleUploadEvidence(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !evidenceFile) {
      setEvidenceErrorMessage("Select a supporting document to upload.");
      return;
    }

    const form = event.currentTarget;
    setIsUploadingEvidence(true);
    setEvidenceMessage(null);
    setEvidenceErrorMessage(null);
    try {
      await uploadRiskEvidence(
        token,
        loadedRiskId,
        evidenceFile,
        evidenceDescription,
      );
      setEvidenceMessage("Evidence uploaded.");
      setEvidenceFile(null);
      setEvidenceDescription("");
      form.reset();
      await refreshRiskEvidence(loadedRiskId);
    } catch (error) {
      setEvidenceErrorMessage(
        error instanceof ApiError ? error.message : "Unable to upload evidence.",
      );
    } finally {
      setIsUploadingEvidence(false);
    }
  }

  async function handleDownloadEvidence(evidence: RiskEvidenceRead) {
    if (!token) {
      return;
    }
    setDownloadingEvidenceId(evidence.id);
    setEvidenceErrorMessage(null);
    try {
      const blob = await downloadRiskEvidence(token, evidence.id);
      saveBlobAsFile(blob, evidence.original_filename);
    } catch (error) {
      setEvidenceErrorMessage(
        error instanceof ApiError ? error.message : "Unable to download evidence.",
      );
    } finally {
      setDownloadingEvidenceId(null);
    }
  }

  async function handleArchiveEvidence(evidence: RiskEvidenceRead) {
    if (!token) {
      return;
    }
    const archiveReason = window.prompt("Archive reason?");
    if (archiveReason === null) {
      return;
    }

    setArchivingEvidenceId(evidence.id);
    setEvidenceMessage(null);
    setEvidenceErrorMessage(null);
    try {
      await archiveRiskEvidence(token, evidence.id, {
        archive_reason: archiveReason.trim() || null,
      });
      setEvidenceMessage("Evidence archived.");
      await refreshRiskEvidence(loadedRiskId);
    } catch (error) {
      setEvidenceErrorMessage(
        error instanceof ApiError ? error.message : "Unable to archive evidence.",
      );
    } finally {
      setArchivingEvidenceId(null);
    }
  }

  async function refreshRiskMonitoring(riskId: string) {
    if (!token) {
      return;
    }
    setRiskMonitoring({ status: "loading" });
    try {
      const monitoringReviews = await listRiskMonitoringReviews(token, riskId);
      setRiskMonitoring({ status: "success", monitoringReviews });
    } catch (error) {
      setRiskMonitoring({
        status: "error",
        message:
          error instanceof ApiError
            ? error.message
            : "Unable to load monitoring reviews.",
      });
    }
  }

  async function handleCreateMonitoring(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setIsCreatingMonitoring(true);
    setMonitoringMessage(null);
    setMonitoringErrorMessage(null);
    try {
      await createRiskMonitoringReview(token, {
        risk_record_id: loadedRiskId,
        monitoring_owner_user_id: monitoringOwnerUserId.trim() || null,
        review_frequency: monitoringFrequency.trim() || null,
        next_review_date: monitoringNextReviewDate || null,
        review_notes: monitoringNotes.trim() || null,
        effectiveness_review: monitoringEffectivenessReview.trim() || null,
      });
      setMonitoringOwnerUserId("");
      setMonitoringFrequency("");
      setMonitoringNextReviewDate("");
      setMonitoringNotes("");
      setMonitoringEffectivenessReview("");
      setMonitoringMessage("Monitoring review created.");
      await refreshRiskMonitoring(loadedRiskId);
      try {
        const detail = await getRiskDetail(token, loadedRiskId);
        setRiskDetail({ status: "success", detail });
      } catch {
        // The monitoring panel remains usable if refreshing the wider detail fails.
      }
    } catch (error) {
      setMonitoringErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to create monitoring review.",
      );
    } finally {
      setIsCreatingMonitoring(false);
    }
  }

  async function handleCompleteMonitoring(
    monitoringReviewId: string,
    request: RiskMonitoringReviewCompleteRequest,
  ) {
    if (!token) {
      return;
    }
    setCompletingMonitoringId(monitoringReviewId);
    setMonitoringMessage(null);
    setMonitoringErrorMessage(null);
    try {
      await completeRiskMonitoringReview(token, monitoringReviewId, request);
      setMonitoringMessage("Effectiveness Review recorded.");
      await refreshRiskMonitoring(loadedRiskId);
    } catch (error) {
      setMonitoringErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to complete monitoring review.",
      );
    } finally {
      setCompletingMonitoringId(null);
    }
  }

  async function handleCloseMonitoring(
    monitoringReviewId: string,
    closureReason: string,
  ) {
    if (!token) {
      return;
    }
    setClosingMonitoringId(monitoringReviewId);
    setMonitoringMessage(null);
    setMonitoringErrorMessage(null);
    try {
      await closeRiskMonitoringReview(token, monitoringReviewId, {
        closure_reason: closureReason.trim() || null,
      });
      setMonitoringMessage("Monitoring closed.");
      await refreshRiskMonitoring(loadedRiskId);
    } catch (error) {
      setMonitoringErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to close monitoring.",
      );
    } finally {
      setClosingMonitoringId(null);
    }
  }

  return (
    <section className="risk-detail-page" aria-labelledby="risk-detail-heading">
      <Link className="back-link" to="/risks">
        Back to risk records
      </Link>

      {successMessage && (
        <p aria-live="polite" className="workspace-success" role="status">
          {successMessage}
        </p>
      )}

      <header className="risk-detail-header">
        <p className="eyebrow">Risk record</p>
        <h1 id="risk-detail-heading">{getRiskDisplayId(risk)}</h1>
        <div className="risk-detail-tags">
          <span className="status-badge">{risk.domain}</span>
          <span className="status-badge">{risk.workflow_status}</span>
          <span className="status-badge">{risk.lifecycle_status}</span>
        </div>
        <p className="muted-text">
          Created {formatDateTime(risk.created_at)} · Updated {formatDateTime(risk.updated_at)}
        </p>
        <NextActionPanel nextAction={nextAction} />
      </header>

      <section
        className="readiness-card"
        aria-labelledby="risk-detail-readiness-heading"
      >
        <h2 id="risk-detail-readiness-heading">Submission readiness</h2>
        <ul className="readiness-list">
          {submissionReadiness.checks.map((check) => (
            <li
              className={`readiness-item ${check.isComplete ? "complete" : "missing"}`}
              key={check.key}
            >
              <span>{check.label}</span>
              <span
                className={`readiness-status ${check.isComplete ? "complete" : "missing"}`}
              >
                {check.isComplete ? "Complete" : "Missing"}
              </span>
              {risk.workflow_status === "DRAFT" &&
                !check.isComplete &&
                check.actionTo &&
                check.actionLabel && (
                  <Link className="readiness-action" to={check.actionTo}>
                    {check.actionLabel}
                  </Link>
                )}
              {risk.workflow_status === "DRAFT" &&
                check.key === "board_of_origin" &&
                !check.isComplete && (
                  <span className="readiness-guidance">
                    Board assignment is not editable from the risk package.
                  </span>
                )}
            </li>
          ))}
        </ul>
        {risk.workflow_status !== "DRAFT" ? (
          <p className="readiness-summary">
            Submission readiness applied while this risk was in DRAFT. Current
            workflow status: {getRiskPackageStatusLabel(risk)}.
          </p>
        ) : submissionReadiness.isReady ? (
          <p className="readiness-summary success">
            Ready to submit to Board of Origin.
          </p>
        ) : (
          <p className="readiness-summary warning">
            Complete all missing readiness items before submission.
          </p>
        )}
      </section>

      <DetailSection title="Problem description">
        <p className="detail-copy">{risk.problem_description}</p>
      </DetailSection>

      <DetailSection title="Source trigger">
        <p className="detail-copy">{risk.source_trigger || "Not specified."}</p>
      </DetailSection>

      <DetailSection title="Risk package">
        {canEditRiskPackage && (
          <div className="detail-section-action">
            <Link className="button" to={`/risks/${risk.id}/package/edit`}>
              {hasRiskPackageContent
                ? "Edit risk package"
                : "Complete risk package"}
            </Link>
          </div>
        )}
        <dl className="metadata-grid risk-package-metadata">
          <div>
            <dt>System Scope</dt>
            <dd>{formatRecordedText(risk.system_scope)}</dd>
          </div>
          <div>
            <dt>Central Event</dt>
            <dd>{formatRecordedText(risk.central_event)}</dd>
          </div>
          <div>
            <dt>Hazard Statement</dt>
            <dd>{formatRecordedText(risk.hazard_statement)}</dd>
          </div>
          <div>
            <dt>Causes</dt>
            <dd>
              <RiskPackageList values={risk.causes} />
            </dd>
          </div>
          <div>
            <dt>Consequences</dt>
            <dd>
              <RiskPackageList values={risk.consequences} />
            </dd>
          </div>
          <div>
            <dt>Existing Controls</dt>
            <dd>
              <RiskPackageList values={risk.existing_controls} />
            </dd>
          </div>
        </dl>
      </DetailSection>

      <DetailSection title="Ownership and metadata">
        <dl className="metadata-grid">
          <div>
            <dt>Board of Origin / Originating Committee</dt>
            <dd>
              {getBoardOfOriginDisplayName(
                risk.board_of_origin_id,
                boardOfOrigin,
                riskCommittees.status,
              )}
            </dd>
          </div>
          <div>
            <dt>Board of Origin Authority Level</dt>
            <dd>
              {boardOfOrigin?.authority_level ||
                (risk.board_of_origin_id ? "Not available." : "Not assigned.")}
            </dd>
          </div>
          <div>
            <dt>Owner</dt>
            <dd>{risk.owner_user_id || "Not assigned."}</dd>
          </div>
          <div>
            <dt>Created by</dt>
            <dd>{risk.created_by_user_id || "Not specified."}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDateTime(risk.created_at)}</dd>
          </div>
          <div>
            <dt>Last updated</dt>
            <dd>{formatDateTime(risk.updated_at)}</dd>
          </div>
        </dl>
      </DetailSection>

      <DetailSection title="Assessments">
        <div className="detail-section-action assessment-action-row">
          {initialAssessmentExists ? (
            <span className="detail-action-muted">
              Initial assessment already recorded.
            </span>
          ) : (
            <Link className="button" to={`/risks/${risk.id}/assessments/new`}>
              Add initial assessment
            </Link>
          )}
          {residualAssessment ? (
            <span className="detail-action-muted">
              Residual assessment already recorded.
            </span>
          ) : (
            <Link
              className="button"
              to={`/risks/${risk.id}/assessments/residual/new`}
            >
              Add residual assessment
            </Link>
          )}
        </div>
        {actions.length === 0 && (
          <p className="residual-guidance">No mitigation actions recorded yet.</p>
        )}
        {actions.length > 0 && allActionsCompleted && (
          <p className="residual-guidance">
            Mitigation actions completed. Residual assessment may be recorded.
          </p>
        )}
        {actions.length > 0 && !allActionsCompleted && (
          <p className="residual-guidance">
            Some mitigation actions remain open. Confirm whether residual
            assessment is appropriate.
          </p>
        )}
        {assessments.length === 0 ? (
          <p className="detail-empty">No assessments recorded yet.</p>
        ) : (
          <ul className="detail-list">
            {assessments.map((assessment) => (
              <li key={assessment.id}>
                <strong>{assessment.assessment_type || "Assessment"}</strong>
                <span>
                  Severity: {assessment.severity || "Not specified"} · Likelihood: {assessment.likelihood || "Not specified"} · Risk level: {assessment.risk_level || "Not specified"}
                </span>
                {assessment.calculated_score !== null &&
                  assessment.calculated_score !== undefined && (
                    <span>Calculated score: {assessment.calculated_score}</span>
                  )}
                <div className="assessment-flags">
                  <span>Tolerable: {formatOptionalBoolean(assessment.is_tolerable)}</span>
                  <span>Mitigation: {formatOptionalBoolean(assessment.requires_mitigation)}</span>
                  <span>Escalation: {formatOptionalBoolean(assessment.requires_escalation)}</span>
                </div>
                {assessment.rationale && <span>Rationale: {assessment.rationale}</span>}
                <span>
                  Recorded {formatDateTime(assessment.assessed_at || assessment.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </DetailSection>

      <DetailSection title="Mitigation actions">
        <div className="detail-section-action">
          <Link className="button" to={`/risks/${risk.id}/actions/new`}>
            Add mitigation action
          </Link>
        </div>
        {initialAssessment?.requires_mitigation === true && (
          <p className="guidance-note">
            This risk assessment requires mitigation.
          </p>
        )}
        {initialAssessment?.requires_mitigation === false && (
          <p className="guidance-note">
            Mitigation is not required by the current assessment, but actions
            may still be recorded if needed.
          </p>
        )}
        {hasOverdueActions && (
          <p className="action-warning overdue" role="status">
            One or more mitigation actions are overdue.
          </p>
        )}
        {hasActionsDueToday && (
          <p className="action-warning due-today" role="status">
            One or more mitigation actions are due today.
          </p>
        )}
        {actions.length === 0 ? (
          <p className="detail-empty">No mitigation actions recorded yet.</p>
        ) : (
          <ul className="detail-list">
            {actions.map((action) => {
              const dueStatus = getRiskActionDueStatus(action);
              return (
                <li
                  className={`risk-action-item ${getRiskActionDueStatusTone(dueStatus)}`}
                  key={action.id}
                >
                  <div className="risk-action-heading">
                    <strong>{action.title || "Untitled action"}</strong>
                    <span
                      className={`action-due-badge ${getRiskActionDueStatusTone(dueStatus)}`}
                    >
                      {getRiskActionDueStatusLabel(dueStatus)}
                    </span>
                  </div>
                  <span>{action.status || "Status not specified"}</span>
                  {action.description && <span>{action.description}</span>}
                  <div className="action-metadata">
                    <span>
                      Action Owner: {action.action_owner_user_id || "Not assigned"}
                    </span>
                    <span>Due Date: {action.due_date || "Not scheduled"}</span>
                    {action.completed_at && (
                      <span>Completed: {formatDateTime(action.completed_at)}</span>
                    )}
                  </div>
                  {action.completion_notes && (
                    <span>Completion notes: {action.completion_notes}</span>
                  )}
                  {isActionCompleted(action) ? (
                    <span className="completed-action-status">Action completed.</span>
                  ) : isRiskActionOpen(action) ? (
                    <Link
                      className="action-inline-button"
                      to={`/risks/${risk.id}/actions/${action.id}/complete`}
                    >
                      Complete action
                    </Link>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </DetailSection>

      <DetailSection title="Committee decisions">
        <div className="detail-section-action">
          <Link className="button" to={`/risks/${risk.id}/decisions/new`}>
            Record committee decision
          </Link>
        </div>
        {decisions.length === 0 ? (
          <p className="detail-empty">No committee decisions recorded yet.</p>
        ) : (
          <ul className="detail-list">
            {decisions.map((decision) => (
              <li key={decision.id}>
                <strong>{decision.decision_type || "Decision"}</strong>
                <span>{decision.decision_text || "No decision text provided."}</span>
                <div className="decision-metadata">
                  {decision.committee_id && (
                    <span>Committee: {decision.committee_id}</span>
                  )}
                  {decision.decided_by_user_id && (
                    <span>Decided by: {decision.decided_by_user_id}</span>
                  )}
                  {decision.decided_at && (
                    <span>Decided: {formatDateTime(decision.decided_at)}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </DetailSection>

      <DetailSection title="Monitoring / Review Cycle">
        <div className="monitoring-panel">
          <form className="monitoring-form" onSubmit={handleCreateMonitoring}>
            <label htmlFor="monitoring-owner-user-id">
              Monitoring Owner User ID (optional)
            </label>
            <input
              id="monitoring-owner-user-id"
              onChange={(event) => setMonitoringOwnerUserId(event.target.value)}
              placeholder="User UUID"
              type="text"
              value={monitoringOwnerUserId}
            />
            <label htmlFor="monitoring-frequency">Review Frequency</label>
            <input
              id="monitoring-frequency"
              maxLength={100}
              onChange={(event) => setMonitoringFrequency(event.target.value)}
              placeholder="Monthly, Quarterly, Before next flight..."
              type="text"
              value={monitoringFrequency}
            />
            <label htmlFor="monitoring-next-review-date">Next Review Date</label>
            <input
              id="monitoring-next-review-date"
              onChange={(event) =>
                setMonitoringNextReviewDate(event.target.value)
              }
              type="date"
              value={monitoringNextReviewDate}
            />
            <label htmlFor="monitoring-notes">Review Notes</label>
            <textarea
              id="monitoring-notes"
              onChange={(event) => setMonitoringNotes(event.target.value)}
              rows={3}
              value={monitoringNotes}
            />
            <label htmlFor="monitoring-effectiveness-review">
              Effectiveness Review (optional)
            </label>
            <textarea
              id="monitoring-effectiveness-review"
              onChange={(event) =>
                setMonitoringEffectivenessReview(event.target.value)
              }
              rows={3}
              value={monitoringEffectivenessReview}
            />
            <button disabled={isCreatingMonitoring} type="submit">
              {isCreatingMonitoring
                ? "Creating monitoring review..."
                : "Create monitoring review"}
            </button>
          </form>

          {monitoringMessage && (
            <p className="monitoring-success" role="status">
              {monitoringMessage}
            </p>
          )}
          {monitoringErrorMessage && (
            <p className="monitoring-warning" role="alert">
              {monitoringErrorMessage}
            </p>
          )}
          {riskMonitoring.status === "loading" && (
            <p aria-live="polite" className="workspace-status" role="status">
              Loading monitoring reviews...
            </p>
          )}
          {riskMonitoring.status === "error" && (
            <div className="workspace-alert" role="alert">
              <strong>Unable to load monitoring reviews.</strong>
              <span>{riskMonitoring.message}</span>
            </div>
          )}
          {riskMonitoring.status === "success" &&
            riskMonitoring.monitoringReviews.length === 0 && (
              <p className="detail-empty">No monitoring reviews recorded yet.</p>
            )}
          {riskMonitoring.status === "success" &&
            riskMonitoring.monitoringReviews.length > 0 && (
              <MonitoringReviewList
                closingMonitoringId={closingMonitoringId}
                completingMonitoringId={completingMonitoringId}
                monitoringReviews={riskMonitoring.monitoringReviews}
                onClose={handleCloseMonitoring}
                onComplete={handleCompleteMonitoring}
              />
            )}
        </div>
      </DetailSection>

      <DetailSection title="Evidence / Supporting Documents">
        <div className="evidence-panel">
          <form className="evidence-upload-form" onSubmit={handleUploadEvidence}>
            <label htmlFor="evidence-file">Supporting document</label>
            <input
              id="evidence-file"
              name="evidence-file"
              onChange={(event) =>
                setEvidenceFile(event.target.files?.[0] ?? null)
              }
              required
              type="file"
            />
            <label htmlFor="evidence-description">Description (optional)</label>
            <textarea
              id="evidence-description"
              name="evidence-description"
              onChange={(event) => setEvidenceDescription(event.target.value)}
              rows={3}
              value={evidenceDescription}
            />
            <button disabled={isUploadingEvidence} type="submit">
              {isUploadingEvidence ? "Uploading evidence..." : "Upload evidence"}
            </button>
          </form>

          {evidenceMessage && (
            <p aria-live="polite" className="evidence-success" role="status">
              {evidenceMessage}
            </p>
          )}
          {evidenceErrorMessage && (
            <p className="evidence-warning" role="alert">
              {evidenceErrorMessage}
            </p>
          )}

          {riskEvidence.status === "loading" && (
            <p aria-live="polite" className="workspace-status" role="status">
              Loading evidence...
            </p>
          )}
          {riskEvidence.status === "error" && (
            <div aria-live="polite" className="workspace-alert" role="alert">
              <strong>Unable to load evidence.</strong>
              <span>{riskEvidence.message}</span>
            </div>
          )}
          {riskEvidence.status === "success" &&
            riskEvidence.evidenceItems.length === 0 && (
              <p className="evidence-empty">No evidence attached yet.</p>
            )}
          {riskEvidence.status === "success" &&
            riskEvidence.evidenceItems.length > 0 && (
              <EvidenceList
                archivingEvidenceId={archivingEvidenceId}
                downloadingEvidenceId={downloadingEvidenceId}
                evidenceItems={riskEvidence.evidenceItems}
                onArchive={handleArchiveEvidence}
                onDownload={handleDownloadEvidence}
              />
            )}

          <section
            className="evidence-package-panel"
            aria-labelledby="evidence-package-heading"
          >
            <div>
              <h3 id="evidence-package-heading">Evidence Package Export</h3>
              <p>
                Generate a controlled ZIP package containing the Risk Dossier,
                active evidence files, manifest, and package readme.
              </p>
            </div>
            <div className="evidence-package-options">
              <label>
                <input
                  checked={includeArchivedEvidence}
                  onChange={(event) =>
                    setIncludeArchivedEvidence(event.target.checked)
                  }
                  type="checkbox"
                />
                Include archived evidence
              </label>
              <label>
                <input
                  checked={includeRiskDossier}
                  onChange={(event) =>
                    setIncludeRiskDossier(event.target.checked)
                  }
                  type="checkbox"
                />
                Include Risk Dossier
              </label>
            </div>
            <div className="evidence-package-actions">
              <button
                disabled={isGeneratingEvidencePackage}
                onClick={() => void handleGenerateEvidencePackage()}
                type="button"
              >
                {isGeneratingEvidencePackage
                  ? "Generating Evidence Package..."
                  : "Generate Evidence Package"}
              </button>
            </div>

            {evidencePackageError && (
              <p className="evidence-package-warning" role="alert">
                {evidencePackageError}
              </p>
            )}

            {evidencePackageReport && (
              <article className="evidence-package-card" aria-live="polite">
                <div>
                  <strong>Risk Evidence Package</strong>
                  <span>
                    Generated {formatDateTime(evidencePackageReport.generated_at)}
                  </span>
                </div>
                <button
                  disabled={isDownloadingEvidencePackage}
                  onClick={() => void handleDownloadEvidencePackage()}
                  type="button"
                >
                  {isDownloadingEvidencePackage
                    ? "Downloading..."
                    : "Download ZIP"}
                </button>
              </article>
            )}
          </section>
        </div>
      </DetailSection>

      <DetailSection title="Audit trail">
        {riskAuditTrail.status === "loading" && (
          <p aria-live="polite" className="workspace-status" role="status">
            Loading audit trail...
          </p>
        )}

        {riskAuditTrail.status === "error" && (
          <div aria-live="polite" className="workspace-alert" role="alert">
            <strong>Unable to load audit trail.</strong>
            <span>{riskAuditTrail.message}</span>
          </div>
        )}

        {riskAuditWarning && (
          <p className="audit-warning" role="status">
            {riskAuditWarning}
          </p>
        )}

        {riskAuditTrail.status === "success" &&
          riskAuditTrail.auditLogs.length === 0 && (
            <p className="audit-empty">
              No audit records available for this risk package.
            </p>
          )}

        {riskAuditTrail.status === "success" &&
          riskAuditTrail.auditLogs.length > 0 && (
            <AuditLogList auditLogs={riskAuditTrail.auditLogs} />
          )}
      </DetailSection>

      <DetailSection title="Reports">
        <div className="report-panel">
          <div>
            <p>
              Generate and download risk dossier reports for this risk record.
            </p>
          </div>
          <button
            disabled={isGeneratingReport}
            onClick={handleGenerateReport}
            type="button"
          >
            {isGeneratingReport ? "Generating report..." : "Generate risk dossier"}
          </button>
        </div>

        {reportMessage && (
          <p aria-live="polite" className="workspace-success" role="status">
            {reportMessage}
          </p>
        )}

        {reportErrorMessage && (
          <p className="report-error" role="alert">
            {reportErrorMessage}
          </p>
        )}

        {riskReports.status === "loading" && (
          <p aria-live="polite" className="workspace-status" role="status">
            Loading generated reports...
          </p>
        )}

        {riskReports.status === "error" && (
          <div aria-live="polite" className="workspace-alert" role="alert">
            <strong>Unable to load generated reports.</strong>
            <span>{riskReports.message}</span>
          </div>
        )}

        {riskReports.status === "success" && riskReports.reports.length === 0 && (
          <p className="detail-empty">No reports generated for this risk yet.</p>
        )}

        {riskReports.status === "success" && riskReports.reports.length > 0 && (
          <ReportList
            downloadingReportId={downloadingReportId}
            onDownload={handleDownloadReport}
            reports={riskReports.reports}
          />
        )}
      </DetailSection>
    </section>
  );
}

function MonitoringReviewList({
  closingMonitoringId,
  completingMonitoringId,
  monitoringReviews,
  onClose,
  onComplete,
}: {
  closingMonitoringId: string | null;
  completingMonitoringId: string | null;
  monitoringReviews: RiskMonitoringReviewRead[];
  onClose: (monitoringReviewId: string, closureReason: string) => Promise<void>;
  onComplete: (
    monitoringReviewId: string,
    request: RiskMonitoringReviewCompleteRequest,
  ) => Promise<void>;
}) {
  return (
    <ul className="monitoring-list">
      {monitoringReviews.map((monitoringReview) => (
        <MonitoringReviewItem
          isClosing={closingMonitoringId === monitoringReview.id}
          isCompleting={completingMonitoringId === monitoringReview.id}
          key={monitoringReview.id}
          monitoringReview={monitoringReview}
          onClose={onClose}
          onComplete={onComplete}
        />
      ))}
    </ul>
  );
}

function MonitoringReviewItem({
  isClosing,
  isCompleting,
  monitoringReview,
  onClose,
  onComplete,
}: {
  isClosing: boolean;
  isCompleting: boolean;
  monitoringReview: RiskMonitoringReviewRead;
  onClose: (monitoringReviewId: string, closureReason: string) => Promise<void>;
  onComplete: (
    monitoringReviewId: string,
    request: RiskMonitoringReviewCompleteRequest,
  ) => Promise<void>;
}) {
  const [effectivenessReview, setEffectivenessReview] = useState("");
  const [reviewOutcome, setReviewOutcome] =
    useState<RiskMonitoringReviewOutcome>("CONTINUE_MONITORING");
  const [nextReviewDate, setNextReviewDate] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [closureReason, setClosureReason] = useState("");
  const isOpen =
    monitoringReview.is_active &&
    !["CLOSED", "CANCELLED"].includes(monitoringReview.status);

  async function submitEffectivenessReview(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    await onComplete(monitoringReview.id, {
      effectiveness_review: effectivenessReview.trim(),
      review_outcome: reviewOutcome,
      next_review_date: nextReviewDate || null,
      review_notes: reviewNotes.trim() || null,
    });
  }

  async function submitClosure(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onClose(monitoringReview.id, closureReason);
  }

  return (
    <li className="monitoring-item">
      <div className="monitoring-item-header">
        <strong>Review Cycle</strong>
        <span
          className={`monitoring-status ${monitoringReview.status.toLowerCase()}`}
        >
          {formatEnumLabel(monitoringReview.status)}
        </span>
      </div>
      <dl className="monitoring-metadata">
        <div>
          <dt>Monitoring Owner</dt>
          <dd>{monitoringReview.monitoring_owner_user_id || "Not assigned"}</dd>
        </div>
        <div>
          <dt>Review Frequency</dt>
          <dd>{monitoringReview.review_frequency || "Not specified"}</dd>
        </div>
        <div>
          <dt>Next Review Date</dt>
          <dd>{monitoringReview.next_review_date || "Not scheduled"}</dd>
        </div>
        <div>
          <dt>Last Reviewed At</dt>
          <dd>{formatDateTime(monitoringReview.last_reviewed_at)}</dd>
        </div>
        <div>
          <dt>Review Outcome</dt>
          <dd>
            {monitoringReview.review_outcome
              ? formatEnumLabel(monitoringReview.review_outcome)
              : "Not recorded"}
          </dd>
        </div>
      </dl>
      {monitoringReview.effectiveness_review && (
        <p>
          <strong>Effectiveness Review:</strong>{" "}
          {monitoringReview.effectiveness_review}
        </p>
      )}
      {monitoringReview.review_notes && (
        <p>
          <strong>Review Notes:</strong> {monitoringReview.review_notes}
        </p>
      )}
      {monitoringReview.closure_reason && (
        <p>
          <strong>Closure Reason:</strong> {monitoringReview.closure_reason}
        </p>
      )}
      {isOpen && (
        <div className="monitoring-actions">
          <form
            className="monitoring-review-form"
            onSubmit={submitEffectivenessReview}
          >
            <h3>Complete Effectiveness Review</h3>
            <label htmlFor={`effectiveness-review-${monitoringReview.id}`}>
              Effectiveness Review
            </label>
            <textarea
              id={`effectiveness-review-${monitoringReview.id}`}
              onChange={(event) => setEffectivenessReview(event.target.value)}
              required
              rows={3}
              value={effectivenessReview}
            />
            <label htmlFor={`review-outcome-${monitoringReview.id}`}>
              Review Outcome
            </label>
            <select
              id={`review-outcome-${monitoringReview.id}`}
              onChange={(event) =>
                setReviewOutcome(
                  event.target.value as RiskMonitoringReviewOutcome,
                )
              }
              value={reviewOutcome}
            >
              <option value="CONTINUE_MONITORING">Continue Monitoring</option>
              <option value="EFFECTIVE_CONTROLS">Effective Controls</option>
              <option value="CONTROLS_NOT_EFFECTIVE">
                Controls Not Effective
              </option>
              <option value="REASSESSMENT_REQUIRED">
                Reassessment Required
              </option>
              <option value="ESCALATION_RECOMMENDED">
                Escalation Recommended
              </option>
              <option value="CLOSE_MONITORING">Close Monitoring</option>
            </select>
            <label htmlFor={`review-next-date-${monitoringReview.id}`}>
              Next Review Date (optional)
            </label>
            <input
              id={`review-next-date-${monitoringReview.id}`}
              onChange={(event) => setNextReviewDate(event.target.value)}
              type="date"
              value={nextReviewDate}
            />
            <label htmlFor={`review-notes-${monitoringReview.id}`}>
              Review Notes (optional)
            </label>
            <textarea
              id={`review-notes-${monitoringReview.id}`}
              onChange={(event) => setReviewNotes(event.target.value)}
              rows={2}
              value={reviewNotes}
            />
            <button disabled={isCompleting || isClosing} type="submit">
              {isCompleting ? "Completing review..." : "Complete Review"}
            </button>
          </form>
          <form className="monitoring-review-form" onSubmit={submitClosure}>
            <h3>Close Monitoring</h3>
            <label htmlFor={`closure-reason-${monitoringReview.id}`}>
              Closure Reason (optional)
            </label>
            <textarea
              id={`closure-reason-${monitoringReview.id}`}
              onChange={(event) => setClosureReason(event.target.value)}
              rows={2}
              value={closureReason}
            />
            <button disabled={isClosing || isCompleting} type="submit">
              {isClosing ? "Closing monitoring..." : "Close Monitoring"}
            </button>
          </form>
        </div>
      )}
    </li>
  );
}

function EvidenceList({
  archivingEvidenceId,
  downloadingEvidenceId,
  evidenceItems,
  onArchive,
  onDownload,
}: {
  archivingEvidenceId: string | null;
  downloadingEvidenceId: string | null;
  evidenceItems: RiskEvidenceRead[];
  onArchive: (evidence: RiskEvidenceRead) => void;
  onDownload: (evidence: RiskEvidenceRead) => void;
}) {
  return (
    <ul className="evidence-list">
      {evidenceItems.map((evidence) => (
        <li className="evidence-item" key={evidence.id}>
          <div>
            <strong>{evidence.original_filename}</strong>
            {evidence.description && <p>{evidence.description}</p>}
            <div className="evidence-metadata">
              <span>{evidence.content_type || "Content type not provided"}</span>
              <span>{formatFileSize(evidence.file_size_bytes)}</span>
              <span>Uploaded {formatDateTime(evidence.uploaded_at)}</span>
              <span>{evidence.is_active ? "Active" : "Archived"}</span>
            </div>
            {evidence.archive_reason && (
              <p>Archive reason: {evidence.archive_reason}</p>
            )}
          </div>
          <div className="evidence-actions">
            <button
              disabled={downloadingEvidenceId === evidence.id}
              onClick={() => onDownload(evidence)}
              type="button"
            >
              {downloadingEvidenceId === evidence.id
                ? "Downloading..."
                : "Download"}
            </button>
            {evidence.is_active && (
              <button
                disabled={archivingEvidenceId === evidence.id}
                onClick={() => onArchive(evidence)}
                type="button"
              >
                {archivingEvidenceId === evidence.id ? "Archiving..." : "Archive"}
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

function ReportList({
  downloadingReportId,
  onDownload,
  reports,
}: {
  downloadingReportId: string | null;
  onDownload: (report: GeneratedReportRead) => void;
  reports: GeneratedReportRead[];
}) {
  return (
    <ul className="report-list">
      {reports.map((report) => (
        <li className="report-item" key={report.id}>
          <div>
            <strong>{formatReportType(report.report_type)}</strong>
            <div className="report-meta">
              <span>Generated {formatDateTime(report.generated_at)}</span>
              {report.generated_by_user_id && (
                <span>Generated by {report.generated_by_user_id}</span>
              )}
            </div>
          </div>
          <div className="report-actions">
            <button
              className="report-download-button"
              disabled={downloadingReportId === report.id}
              onClick={() => onDownload(report)}
              type="button"
            >
              {downloadingReportId === report.id
                ? "Downloading..."
                : getReportDownloadLabel(report.report_type)}
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

function NextActionPanel({ nextAction }: { nextAction: NextAction }) {
  return (
    <section
      className={`next-action-panel next-action-${nextAction.statusTone}`}
      aria-labelledby="next-action-heading"
    >
      <div className="next-action-content">
        <div>
          <p className="eyebrow">Recommended next step</p>
          <h2 id="next-action-heading">{nextAction.title}</h2>
          <p>{nextAction.description}</p>
        </div>
        {nextAction.linkTo && nextAction.linkLabel && (
          <Link className="button" to={nextAction.linkTo}>
            {nextAction.linkLabel}
          </Link>
        )}
      </div>
      <ul className="next-action-checklist">
        {nextAction.checklist.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function DetailSection({
  children,
  title,
}: {
  children: React.ReactNode;
  title: string;
}) {
  return (
    <section className="detail-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function RiskPackageList({ values }: { values: string[] | null | undefined }) {
  const recordedValues = Array.from(
    new Set((values ?? []).map((value) => value.trim()).filter(Boolean)),
  );
  if (recordedValues.length === 0) {
    return <>Not recorded</>;
  }

  return (
    <ul className="risk-package-detail-list">
      {recordedValues.map((value) => (
        <li key={value}>{value}</li>
      ))}
    </ul>
  );
}

function getRiskRecord(detail: RiskDetailResponse): RiskRecordRead | null {
  return detail.risk || detail.risk_record || detail.record || null;
}

function formatRecordedText(value: string | null | undefined): string {
  return value?.trim() || "Not recorded";
}

function hasAnyRiskPackageContent(risk: RiskRecordRead): boolean {
  return (
    Boolean(risk.system_scope?.trim()) ||
    Boolean(risk.central_event?.trim()) ||
    Boolean(risk.hazard_statement?.trim()) ||
    Boolean(risk.causes?.some((value) => value.trim())) ||
    Boolean(risk.consequences?.some((value) => value.trim())) ||
    Boolean(risk.existing_controls?.some((value) => value.trim()))
  );
}

function canUserUpdateRiskPackage(
  risk: RiskRecordRead,
  userId: string | undefined,
): boolean {
  if (!userId) {
    return false;
  }
  if (risk.owner_user_id) {
    return risk.owner_user_id === userId;
  }
  return Boolean(risk.created_by_user_id && risk.created_by_user_id === userId);
}

async function loadRiskAuditTrail({
  token,
  risk,
  assessments,
  actions,
  decisions,
  monitoringReviews,
  reports,
}: {
  token: string;
  risk: RiskRecordRead;
  assessments: RiskAssessmentRead[];
  actions: RiskActionRead[];
  decisions: RiskDecisionRead[];
  monitoringReviews: RiskMonitoringReviewRead[];
  reports: GeneratedReportRead[];
}): Promise<RiskAuditTrailResult> {
  const requests = [
    listAuditLogs(token, {
      entityType: "RiskRecord",
      entityId: risk.id,
      limit: 50,
    }),
    ...assessments.map((assessment) =>
      listAuditLogs(token, {
        entityType: "RiskAssessment",
        entityId: assessment.id,
        limit: 50,
      }),
    ),
    ...actions.map((action) =>
      listAuditLogs(token, {
        entityType: "RiskAction",
        entityId: action.id,
        limit: 50,
      }),
    ),
    ...decisions.map((decision) =>
      listAuditLogs(token, {
        entityType: "RiskDecision",
        entityId: decision.id,
        limit: 50,
      }),
    ),
    ...monitoringReviews.map((monitoringReview) =>
      listAuditLogs(token, {
        entityType: "RiskMonitoringReview",
        entityId: monitoringReview.id,
        limit: 50,
      }),
    ),
    ...reports.map((report) =>
      listAuditLogs(token, {
        entityType: "GeneratedReport",
        entityId: report.id,
        limit: 50,
      }),
    ),
  ];
  const results = await Promise.allSettled(requests);
  const successfulResults = results.filter(
    (result): result is PromiseFulfilledResult<AuditLogRead[]> =>
      result.status === "fulfilled",
  );

  if (successfulResults.length === 0) {
    throw new Error("Unable to load audit trail");
  }

  return {
    auditLogs: uniqueAuditLogs(
      successfulResults.flatMap((result) => result.value),
    ),
    failedScopeCount: results.length - successfulResults.length,
  };
}

function uniqueAuditLogs(logs: AuditLogRead[]): AuditLogRead[] {
  return Array.from(new Map(logs.map((log) => [log.id, log])).values()).sort(
    (first, second) =>
      getDateTimeValue(second.changed_at) - getDateTimeValue(first.changed_at),
  );
}

function getDateTimeValue(value: string): number {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

function getBoardOfOriginDisplayName(
  boardOfOriginId: string | null | undefined,
  boardOfOrigin: CommitteeRead | undefined,
  committeeStatus: RiskCommitteesState["status"],
): string {
  if (!boardOfOriginId) {
    return "Not assigned.";
  }

  if (boardOfOrigin) {
    return boardOfOrigin.name;
  }

  return committeeStatus === "loading"
    ? `${boardOfOriginId} - Loading committee details...`
    : `${boardOfOriginId} - Committee name not available.`;
}

function getNextAction({
  risk,
  assessments,
  actions,
  decisions,
  canEditRiskPackage,
}: {
  risk: RiskRecordRead;
  assessments: RiskAssessmentRead[];
  actions: RiskActionRead[];
  decisions: RiskDecisionRead[];
  canEditRiskPackage: boolean;
}): NextAction {
  const initialAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const residualAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "RESIDUAL",
  );
  const openActions = actions.filter(isRiskActionOpen);
  const completedActions = actions.filter(isActionCompleted);
  const submissionReadiness = getRiskSubmissionReadiness(risk, assessments);
  const hasInitialAssessment = submissionReadiness.hasInitialAssessment;
  const hasResidualAssessment = Boolean(residualAssessment);
  const hasActions = actions.length > 0;
  const hasOpenActions = openActions.length > 0;
  const hasCompletedActions = completedActions.length > 0;
  const lastDecision = getLatestDecision(decisions);

  if (risk.workflow_status === "CLOSED" || risk.lifecycle_status === "CLOSED") {
    return {
      title: "Risk closed",
      description: "This risk has completed the active workflow.",
      statusTone: "success",
      checklist: [
        "Risk lifecycle is closed.",
        "Review audit trail or reports if evidence is required.",
      ],
    };
  }

  if (risk.workflow_status === "ACCEPTED") {
    return {
      title: "Risk accepted",
      description:
        "Residual risk has been accepted. Confirm whether closure or monitoring is required by the committee.",
      linkLabel: "Record committee decision",
      linkTo: `/risks/${risk.id}/decisions/new`,
      statusTone: "success",
      checklist: [
        "Residual risk accepted.",
        "Closure or monitoring may be the next governance step.",
      ],
    };
  }

  if (risk.workflow_status === "REJECTED") {
    return {
      title: "Risk rejected",
      description: "This risk was rejected by committee decision.",
      statusTone: "blocked",
      checklist: [
        lastDecision
          ? `Latest decision: ${lastDecision.decision_type || "Decision recorded"}.`
          : "Review committee decision text.",
        "Create a new risk record if the issue needs to be re-submitted.",
      ],
    };
  }

  if (risk.workflow_status === "RETURNED_FOR_REVISION") {
    return {
      title: "Risk returned for revision",
      description:
        "Review committee comments and update the risk package before re-submission.",
      statusTone: "warning",
      checklist: [
        lastDecision
          ? `Latest decision: ${lastDecision.decision_type || "Decision recorded"}.`
          : "Review decision comments.",
        "Update the risk package as required.",
      ],
    };
  }

  if (risk.workflow_status === "DRAFT" && !submissionReadiness.hasBoardOfOrigin) {
    return {
      title: "Assign Board of Origin",
      description:
        "Assign the originating LOW operational board before submission.",
      statusTone: "warning",
      checklist: [
        "Board of Origin / Originating Committee is not assigned.",
        "A Board of Origin is required before submission.",
      ],
    };
  }

  if (
    risk.workflow_status === "DRAFT" &&
    !submissionReadiness.packageMinimumComplete
  ) {
    return {
      title: "Complete risk package",
      description:
        "Add system scope, central event, and hazard statement before initial assessment.",
      linkLabel: canEditRiskPackage ? "Complete risk package" : undefined,
      linkTo: canEditRiskPackage ? `/risks/${risk.id}/package/edit` : undefined,
      statusTone: "warning",
      checklist: [
        ...submissionReadiness.checks
          .filter(
            (check) =>
              ["system_scope", "central_event", "hazard_statement"].includes(
                check.key,
              ) && !check.isComplete,
          )
          .map((check) => `${check.label} is not recorded.`),
        "Causes, consequences, and existing controls are recommended.",
      ],
    };
  }

  if (risk.workflow_status === "DRAFT" && !hasInitialAssessment) {
    return {
      title: "Complete initial assessment",
      description:
        "Record the initial risk assessment before submitting the risk to committee review.",
      linkLabel: "Add initial assessment",
      linkTo: `/risks/${risk.id}/assessments/initial/new`,
      statusTone: "warning",
      checklist: [
        "Problem description recorded.",
        "Initial assessment missing.",
        "Risk not yet submitted.",
      ],
    };
  }

  if (risk.workflow_status === "DRAFT" && hasInitialAssessment) {
    return {
      title: "Submit risk for committee review",
      description:
        "Initial assessment is recorded. Submit the risk to the operational board when the package is ready.",
      linkLabel: "Submit risk",
      linkTo: `/risks/${risk.id}/submit`,
      statusTone: "info",
      checklist: [
        "Initial assessment recorded.",
        "Risk still in draft.",
        "Submission will start committee workflow.",
      ],
    };
  }

  if (isOperationalBoardReviewStatus(risk.workflow_status)) {
    if (!hasInitialAssessment) {
      return {
        title: "Initial assessment missing",
        description:
          "The risk has been submitted but no initial assessment is recorded. Add the initial assessment before committee decision.",
        linkLabel: "Add initial assessment",
        linkTo: `/risks/${risk.id}/assessments/new`,
        statusTone: "warning",
        checklist: ["Risk submitted.", "Initial assessment missing."],
      };
    }

    return {
      title: "Awaiting operational board decision",
      description:
        "This risk is ready for operational board review. Active committee members can record a decision.",
      linkLabel: "Record committee decision",
      linkTo: `/risks/${risk.id}/decisions/new`,
      statusTone: "info",
      checklist: [
        "Risk submitted.",
        "Initial assessment recorded.",
        "Committee decision pending.",
      ],
    };
  }

  if (initialAssessment?.requires_mitigation === true && actions.length === 0) {
    return {
      title: "Define mitigation action",
      description:
        "The initial assessment requires mitigation. Add at least one mitigation action.",
      linkLabel: "Add mitigation action",
      linkTo: `/risks/${risk.id}/actions/new`,
      statusTone: "warning",
      checklist: ["Mitigation required.", "No mitigation actions recorded."],
    };
  }

  if (hasActions && hasOpenActions) {
    const singleOpenAction = openActions.length === 1 ? openActions[0] : undefined;

    return {
      title: "Complete mitigation actions",
      description:
        "Mitigation actions are open. Complete or cancel them before residual acceptance or closure.",
      linkLabel: singleOpenAction ? "Complete action" : undefined,
      linkTo: singleOpenAction
        ? `/risks/${risk.id}/actions/${singleOpenAction.id}/complete`
        : undefined,
      statusTone: "warning",
      checklist: [
        `${openActions.length} open mitigation action(s).`,
        "Residual closure should wait until actions are completed or cancelled.",
      ],
    };
  }

  if (hasActions && !hasOpenActions && !hasResidualAssessment) {
    return {
      title: "Record residual risk assessment",
      description:
        "Mitigation actions are complete or closed. Record the residual risk assessment.",
      linkLabel: "Add residual assessment",
      linkTo: `/risks/${risk.id}/assessments/residual/new`,
      statusTone: "info",
      checklist: [
        hasCompletedActions
          ? "Mitigation actions complete or closed."
          : "Mitigation actions are closed.",
        "Residual assessment missing.",
      ],
    };
  }

  if (
    initialAssessment?.requires_mitigation === false &&
    !hasResidualAssessment &&
    risk.workflow_status !== "DRAFT"
  ) {
    return {
      title: "Consider residual risk assessment",
      description:
        "Mitigation may not be required, but residual risk review may be needed before acceptance or closure.",
      linkLabel: "Add residual assessment",
      linkTo: `/risks/${risk.id}/assessments/residual/new`,
      statusTone: "info",
      checklist: [
        "Initial assessment does not require mitigation.",
        "Residual assessment not recorded.",
      ],
    };
  }

  if (residualAssessment) {
    if (residualAssessment.requires_escalation === true) {
      return {
        title: "Escalate residual risk",
        description: "Residual risk requires escalation to the next authority level.",
        linkLabel: "Record committee decision",
        linkTo: `/risks/${risk.id}/decisions/new`,
        statusTone: "warning",
        checklist: [
          "Residual assessment recorded.",
          "Residual risk requires escalation.",
          "Committee decision should escalate the risk.",
        ],
      };
    }

    if (residualAssessment.is_tolerable === true && !hasOpenActions) {
      return {
        title: "Accept or close residual risk",
        description:
          "Residual risk is tolerable and actions are complete. Committee may accept residual risk or close the risk if appropriate.",
        linkLabel: "Record committee decision",
        linkTo: `/risks/${risk.id}/decisions/new`,
        statusTone: "success",
        checklist: [
          "Residual assessment recorded.",
          "Residual risk tolerable.",
          "No open mitigation actions.",
        ],
      };
    }

    if (residualAssessment.is_tolerable === false) {
      return {
        title: "Residual risk not tolerable",
        description:
          "Residual risk is not tolerable. Additional mitigation or escalation is required.",
        linkLabel: "Record committee decision",
        linkTo: `/risks/${risk.id}/decisions/new`,
        statusTone: "warning",
        checklist: [
          "Residual assessment recorded.",
          "Residual risk not tolerable.",
          "Escalation or further mitigation may be required.",
        ],
      };
    }
  }

  return {
    title: "Review risk package",
    description:
      "Review the available assessments, actions, and committee decisions to determine the next workflow step.",
    statusTone: "info",
    checklist: [
      `Workflow status: ${risk.workflow_status}`,
      `Lifecycle status: ${risk.lifecycle_status}`,
    ],
  };
}

function isOperationalBoardReviewStatus(status: string): boolean {
  return [
    "SUBMITTED_TO_OPERATIONAL_BOARD",
    "UNDER_OPERATIONAL_BOARD_REVIEW",
  ].includes(status);
}

function getLatestDecision(
  decisions: RiskDecisionRead[],
): RiskDecisionRead | undefined {
  return [...decisions].sort(
    (first, second) => getDecisionTime(second) - getDecisionTime(first),
  )[0];
}

function getDecisionTime(decision: RiskDecisionRead): number {
  const date = new Date(decision.decided_at || decision.created_at || "");

  return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not available" : date.toLocaleString();
}

function formatOptionalBoolean(value: boolean | null | undefined): string {
  if (value === null || value === undefined) {
    return "Not specified";
  }

  return value ? "Yes" : "No";
}

function formatReportType(value: string): string {
  const labels: Record<string, string> = {
    RISK_DOSSIER_DOCX: "Risk Dossier",
    COMMITTEE_MEETING_PACK_DOCX: "Committee Meeting Pack",
    COMMITTEE_MEETING_MINUTES_DOCX: "Committee Meeting Minutes",
    RISK_EVIDENCE_PACKAGE_ZIP: "Risk Evidence Package",
  };
  return labels[value] || value.replace(/_/g, " ") || "Report";
}

function getReportDownloadLabel(reportType: string): string {
  return reportType.endsWith("_ZIP") ? "Download ZIP" : "Download DOCX";
}

function formatEnumLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isActionCompleted(action: {
  status?: string | null;
  completed_at?: string | null;
}): boolean {
  return (
    action.status === "COMPLETED" ||
    Boolean(action.completed_at)
  );
}

function getSuccessMessage(state: unknown): string | null {
  if (
    !state ||
    typeof state !== "object" ||
    !("successMessage" in state) ||
    typeof state.successMessage !== "string"
  ) {
    return null;
  }

  return state.successMessage;
}
