import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useParams } from "react-router-dom";

import { listAuditLogs } from "../api/auditLogs";
import { ApiError } from "../api/client";
import { listCommittees } from "../api/committees";
import {
  downloadGeneratedReport,
  generateRiskDossierReport,
  listGeneratedReports,
  saveBlobAsFile,
} from "../api/reports";
import { getRiskDetail } from "../api/risks";
import type {
  AuditLogRead,
  CommitteeRead,
  GeneratedReportRead,
  RiskActionRead,
  RiskAssessmentRead,
  RiskDecisionRead,
  RiskDetailResponse,
  RiskRecordRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AuditLogList } from "../components/AuditLogList";

type RiskDetailState =
  | { status: "loading" }
  | { status: "success"; detail: RiskDetailResponse }
  | { status: "error"; message: string };

type RiskReportsState =
  | { status: "idle" | "loading" }
  | { status: "success"; reports: GeneratedReportRead[] }
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
  const { isAuthenticated, token } = useAuth();
  const { riskRecordId } = useParams();
  const location = useLocation();
  const [riskDetail, setRiskDetail] = useState<RiskDetailState>({
    status: "loading",
  });
  const [riskReports, setRiskReports] = useState<RiskReportsState>({
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
          setRiskAuditTrail({ status: "loading" });
          setRiskAuditWarning(null);
          setReportMessage(null);
          setReportErrorMessage(null);
        }

        const detail = await getRiskDetail(tokenToUse, idToLoad);
        if (isCurrent) {
          setRiskDetail({ status: "success", detail });
        }

        const risk = getRiskRecord(detail);
        if (!risk) {
          if (isCurrent) {
            setRiskReports({ status: "idle" });
            setRiskAuditTrail({ status: "idle" });
          }
          return;
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
  const actions = riskDetail.detail.actions ?? [];
  const decisions = riskDetail.detail.decisions ?? [];
  const boardOfOrigin =
    risk.board_of_origin_id && riskCommittees.status === "success"
      ? riskCommittees.committees.find(
          (committee) => committee.id === risk.board_of_origin_id,
        )
      : undefined;
  const initialAssessmentExists = assessments.some(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const initialAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const residualAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "RESIDUAL",
  );
  const nextAction = getNextAction({ risk, assessments, actions, decisions });
  const allActionsCompleted =
    actions.length > 0 && actions.every((action) => isActionCompleted(action));
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

      <DetailSection title="Problem description">
        <p className="detail-copy">{risk.problem_description}</p>
      </DetailSection>

      <DetailSection title="Source trigger">
        <p className="detail-copy">{risk.source_trigger || "Not specified."}</p>
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
        {actions.length === 0 ? (
          <p className="detail-empty">No mitigation actions recorded yet.</p>
        ) : (
          <ul className="detail-list">
            {actions.map((action) => (
              <li key={action.id}>
                <strong>{action.title || "Untitled action"}</strong>
                <span>{action.status || "Status not specified"}</span>
                {action.description && <span>{action.description}</span>}
                <div className="action-metadata">
                  {action.action_owner_user_id && (
                    <span>Owner: {action.action_owner_user_id}</span>
                  )}
                  {action.due_date && <span>Due: {action.due_date}</span>}
                  {action.completed_at && (
                    <span>Completed: {formatDateTime(action.completed_at)}</span>
                  )}
                </div>
                {action.completion_notes && (
                  <span>Completion notes: {action.completion_notes}</span>
                )}
                {isActionCompleted(action) ? (
                  <span className="completed-action-status">Action completed.</span>
                ) : (
                  <Link
                    className="action-inline-button"
                    to={`/risks/${risk.id}/actions/${action.id}/complete`}
                  >
                    Complete action
                  </Link>
                )}
              </li>
            ))}
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
              {downloadingReportId === report.id ? "Downloading..." : "Download DOCX"}
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

function getRiskRecord(detail: RiskDetailResponse): RiskRecordRead | null {
  return detail.risk || detail.risk_record || detail.record || null;
}

async function loadRiskAuditTrail({
  token,
  risk,
  assessments,
  actions,
  decisions,
  reports,
}: {
  token: string;
  risk: RiskRecordRead;
  assessments: RiskAssessmentRead[];
  actions: RiskActionRead[];
  decisions: RiskDecisionRead[];
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
}: {
  risk: RiskRecordRead;
  assessments: RiskAssessmentRead[];
  actions: RiskActionRead[];
  decisions: RiskDecisionRead[];
}): NextAction {
  const initialAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const residualAssessment = assessments.find(
    (assessment) => assessment.assessment_type === "RESIDUAL",
  );
  const openActions = actions.filter(isActionOpen);
  const completedActions = actions.filter(isActionCompleted);
  const hasInitialAssessment = Boolean(initialAssessment);
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

  if (risk.workflow_status === "DRAFT" && !hasInitialAssessment) {
    return {
      title: "Complete initial assessment",
      description:
        "Record the initial risk assessment before submitting the risk to committee review.",
      linkLabel: "Add initial assessment",
      linkTo: `/risks/${risk.id}/assessments/new`,
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

function isActionOpen(action: RiskActionRead): boolean {
  if (action.status === "COMPLETED") {
    return false;
  }

  if (action.completed_at) {
    return false;
  }

  if (action.status === "CANCELLED") {
    return false;
  }

  return true;
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
  return value.replace(/_/g, " ") || "Report";
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
