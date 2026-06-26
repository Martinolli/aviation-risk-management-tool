import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { listCommitteeMembers } from "../api/committeeMembers";
import { listCommittees } from "../api/committees";
import { createRiskDecision } from "../api/riskDecisions";
import { getRiskDetail } from "../api/risks";
import type {
  CommitteeMemberRead,
  CommitteeRead,
  RiskDecisionType,
  RiskActionRead,
  RiskAssessmentRead,
  RiskDetailResponse,
  RiskRecordRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

const DECISION_OPTIONS: { value: RiskDecisionType; label: string }[] = [
  { value: "APPROVE", label: "Approve" },
  { value: "REJECT", label: "Reject" },
  { value: "ESCALATE", label: "Escalate" },
  { value: "RETURN_FOR_REVISION", label: "Return for revision" },
  { value: "ACCEPT_RESIDUAL_RISK", label: "Accept residual risk" },
  { value: "CLOSE", label: "Close" },
];

interface DecisionOptionState {
  value: RiskDecisionType;
  label: string;
  isAvailable: boolean;
  reason?: string;
}

type DecisionPageState =
  | { status: "loading" }
  | {
      status: "success";
      detail: RiskDetailResponse;
      committees: CommitteeRead[];
      memberships: CommitteeMemberRead[];
    }
  | { status: "error"; message: string };

export function RiskDecisionCreatePage() {
  const { isAuthenticated, token, user } = useAuth();
  const { riskRecordId } = useParams();
  const navigate = useNavigate();
  const [pageState, setPageState] = useState<DecisionPageState>({
    status: "loading",
  });
  const [committeeId, setCommitteeId] = useState("");
  const [decisionType, setDecisionType] = useState<RiskDecisionType | "">("");
  const [decisionText, setDecisionText] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    if (!token || !riskRecordId || !user?.id) {
      return;
    }

    const tokenToUse = token;
    const idToLoad = riskRecordId;
    const currentUserId = user.id;

    async function loadDecisionContext() {
      try {
        const [detail, committees, memberships] = await Promise.all([
          getRiskDetail(tokenToUse, idToLoad),
          listCommittees(tokenToUse),
          listCommitteeMembers(tokenToUse, { userId: currentUserId }),
        ]);
        if (isCurrent) {
          setPageState({ status: "success", detail, committees, memberships });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setPageState({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
      }
    }

    void loadDecisionContext();

    return () => {
      isCurrent = false;
    };
  }, [riskRecordId, token, user?.id]);

  useEffect(() => {
    if (!decisionType || pageState.status !== "success") {
      return;
    }

    const risk = getRiskRecord(pageState.detail);
    if (!risk) {
      return;
    }

    const selectableCommittees = getSelectableCommittees(
      pageState.committees,
      pageState.memberships,
    );
    const selectedCommittee = selectableCommittees.find(
      (committee) => committee.id === committeeId,
    );
    const residualAssessment = pageState.detail.assessments?.find(
      (assessment) => assessment.assessment_type === "RESIDUAL",
    );
    const decisionOptionStates = getDecisionOptionStates({
      committee: selectedCommittee,
      risk,
      residualAssessment,
      actions: pageState.detail.actions ?? [],
    });
    const isSelectedDecisionAvailable = decisionOptionStates.some(
      (option) => option.value === decisionType && option.isAvailable,
    );

    if (!isSelectedDecisionAvailable) {
      setDecisionType("");
    }
  }, [committeeId, decisionType, pageState]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token || !riskRecordId || pageState.status !== "success") {
      return;
    }

    setErrorMessage(null);

    const selectableCommittees = getSelectableCommittees(
      pageState.committees,
      pageState.memberships,
    );
    const hasSelectedCommittee = selectableCommittees.some(
      (committee) => committee.id === committeeId,
    );
    const selectedCommittee = selectableCommittees.find(
      (committee) => committee.id === committeeId,
    );
    const risk = getRiskRecord(pageState.detail);
    const residualAssessment = pageState.detail.assessments?.find(
      (assessment) => assessment.assessment_type === "RESIDUAL",
    );

    if (!committeeId || !hasSelectedCommittee) {
      setErrorMessage("Select a committee where you are an active member.");
      return;
    }
    if (!decisionType) {
      setErrorMessage("Select a decision type.");
      return;
    }
    if (!risk) {
      setErrorMessage("Unable to load risk detail.");
      return;
    }

    const decisionOptionStates = getDecisionOptionStates({
      committee: selectedCommittee,
      risk,
      residualAssessment,
      actions: pageState.detail.actions ?? [],
    });
    const isDecisionAvailable = decisionOptionStates.some(
      (option) => option.value === decisionType && option.isAvailable,
    );

    if (!isDecisionAvailable) {
      setErrorMessage(
        "Select an available decision type for this committee and risk state.",
      );
      return;
    }
    if (!decisionText.trim()) {
      setErrorMessage("Enter decision text.");
      return;
    }

    setIsSubmitting(true);

    try {
      await createRiskDecision(token, {
        risk_record_id: riskRecordId,
        committee_id: committeeId,
        decision_type: decisionType,
        decision_text: decisionText.trim(),
      });
      navigate(`/risks/${riskRecordId}`, {
        replace: true,
        state: { successMessage: "Committee decision recorded successfully." },
      });
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : "Unable to record committee decision.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (!riskRecordId) {
    return <Navigate replace to="/risks" />;
  }

  if (pageState.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading decision context...
      </p>
    );
  }

  if (pageState.status === "error") {
    return (
      <section className="risk-decision-page" aria-labelledby="decision-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="decision-load-error">Unable to load decision context.</strong>
          <span>{pageState.message}</span>
        </div>
      </section>
    );
  }

  const risk = getRiskRecord(pageState.detail);

  if (!risk) {
    return (
      <section className="risk-decision-page" aria-labelledby="decision-load-error">
        <Link className="back-link" to={`/risks/${riskRecordId}`}>
          Back to risk detail
        </Link>
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="decision-load-error">Unable to load risk detail.</strong>
          <span>The API response did not include a risk record.</span>
        </div>
      </section>
    );
  }

  const initialAssessment = pageState.detail.assessments?.find(
    (assessment) => assessment.assessment_type === "INITIAL",
  );
  const residualAssessment = pageState.detail.assessments?.find(
    (assessment) => assessment.assessment_type === "RESIDUAL",
  );
  const riskActions = pageState.detail.actions ?? [];
  const selectableCommittees = getSelectableCommittees(
    pageState.committees,
    pageState.memberships,
  );
  const selectedCommittee = selectableCommittees.find(
    (committee) => committee.id === committeeId,
  );
  const decisionOptionStates = getDecisionOptionStates({
    committee: selectedCommittee,
    risk,
    residualAssessment,
    actions: riskActions,
  });
  const availableDecisionOptions = decisionOptionStates.filter(
    (option) => option.isAvailable,
  );
  const unavailableDecisionOptions = decisionOptionStates.filter(
    (option) => !option.isAvailable && option.reason,
  );
  const hasSelectableCommittees = selectableCommittees.length > 0;
  const openMitigationActionCount = riskActions.filter(isOpenMitigationAction).length;

  return (
    <section className="risk-decision-page" aria-labelledby="decision-heading">
      <Link className="back-link" to={`/risks/${risk.id}`}>
        Back to risk detail
      </Link>
      <p className="eyebrow">Committee decision</p>
      <h1 id="decision-heading">Record committee decision</h1>

      <section className="decision-summary" aria-labelledby="decision-summary-heading">
        <h2 id="decision-summary-heading">Risk summary</h2>
        <dl className="metadata-grid">
          <div>
            <dt>Risk ID</dt>
            <dd>{getRiskDisplayId(risk)}</dd>
          </div>
          <div>
            <dt>Domain</dt>
            <dd>{risk.domain}</dd>
          </div>
          <div>
            <dt>Workflow status</dt>
            <dd>{risk.workflow_status}</dd>
          </div>
          <div>
            <dt>Lifecycle status</dt>
            <dd>{risk.lifecycle_status}</dd>
          </div>
        </dl>
        <p className="detail-copy">{risk.problem_description}</p>
        <div className="decision-assessment-summary">
          <p>Initial assessment: {getAssessmentSummary(initialAssessment)}</p>
          <p>Residual assessment: {getAssessmentSummary(residualAssessment)}</p>
        </div>
        <div
          className="decision-readiness"
          aria-labelledby="decision-readiness-heading"
        >
          <h3 id="decision-readiness-heading">Decision readiness</h3>
          <dl>
            <div>
              <dt>Residual assessment</dt>
              <dd>{residualAssessment ? "Recorded" : "Not recorded"}</dd>
            </div>
            <div>
              <dt>Residual tolerable</dt>
              <dd>{formatOptionalBoolean(residualAssessment?.is_tolerable)}</dd>
            </div>
            <div>
              <dt>Residual requires escalation</dt>
              <dd>
                {formatOptionalBoolean(residualAssessment?.requires_escalation)}
              </dd>
            </div>
            <div>
              <dt>Open mitigation actions</dt>
              <dd>{openMitigationActionCount}</dd>
            </div>
          </dl>
        </div>
      </section>

      <form className="decision-form" onSubmit={handleSubmit}>
        <label htmlFor="committee-id">Committee</label>
        <select
          disabled={isSubmitting || !hasSelectableCommittees}
          id="committee-id"
          name="committee_id"
          onChange={(event) => setCommitteeId(event.target.value)}
          required
          value={committeeId}
        >
          <option value="">Select committee</option>
          {selectableCommittees.map((committee) => (
            <option key={committee.id} value={committee.id}>
              {getCommitteeOptionLabel(
                committee,
                findMembershipForCommittee(pageState.memberships, committee.id),
              )}
            </option>
          ))}
        </select>
        {hasSelectableCommittees ? (
          <p className="decision-note">
            Showing committees where you are an active member.
          </p>
        ) : (
          <p className="decision-guidance">
            You are not an active member of any decision committee. You cannot
            record committee decisions.
          </p>
        )}

        <label htmlFor="decision-type">Decision type</label>
        <select
          disabled={isSubmitting || !selectedCommittee}
          id="decision-type"
          name="decision_type"
          onChange={(event) => setDecisionType(event.target.value as RiskDecisionType)}
          required
          value={decisionType}
        >
          <option value="">Select decision type</option>
          {availableDecisionOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        {!selectedCommittee && (
          <p className="decision-guidance">
            Select a committee before choosing a decision type.
          </p>
        )}
        {selectedCommittee && unavailableDecisionOptions.length > 0 && (
          <div className="decision-unavailable-list">
            <h3>Unavailable decisions</h3>
            <ul>
              {unavailableDecisionOptions.map((option) => (
                <li className="decision-unavailable-item" key={option.value}>
                  <strong>{option.label}:</strong> {option.reason}
                </li>
              ))}
            </ul>
          </div>
        )}
        {decisionType === "ESCALATE" && (
          <p className="decision-note">
            Escalation should identify the next authority level in the decision
            text.
          </p>
        )}

        <label htmlFor="decision-text">Decision text</label>
        <textarea
          disabled={isSubmitting}
          id="decision-text"
          name="decision_text"
          onChange={(event) => setDecisionText(event.target.value)}
          required
          value={decisionText}
        />

        {errorMessage && (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        )}

        <div className="form-actions">
          <button
            disabled={isSubmitting || !hasSelectableCommittees}
            type="submit"
          >
            {isSubmitting ? "Recording decision..." : "Record committee decision"}
          </button>
          <Link className="secondary-link" to={`/risks/${risk.id}`}>
            Cancel
          </Link>
        </div>
      </form>
    </section>
  );
}

function getRiskRecord(detail: RiskDetailResponse): RiskRecordRead | null {
  return detail.risk || detail.risk_record || detail.record || null;
}

function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

function getAssessmentSummary(assessment: RiskAssessmentRead | undefined): string {
  if (!assessment) {
    return "Not recorded";
  }

  return `${assessment.risk_level || "Risk level not specified"} (${assessment.calculated_score ?? "no score"})`;
}

function getDecisionOptionStates({
  committee,
  risk,
  residualAssessment,
  actions,
}: {
  committee: CommitteeRead | undefined;
  risk: RiskRecordRead;
  residualAssessment: RiskAssessmentRead | undefined;
  actions: RiskActionRead[];
}): DecisionOptionState[] {
  if (!committee) {
    return DECISION_OPTIONS.map((option) => ({
      ...option,
      isAvailable: false,
      reason: "Select a committee first.",
    }));
  }

  if (committee.authority_level === "LOW") {
    return getLowDecisionOptionStates(risk, residualAssessment, actions);
  }

  if (committee.authority_level === "MIDDLE") {
    return getMiddleDecisionOptionStates(risk, residualAssessment, actions);
  }

  if (committee.authority_level === "HIGH") {
    return getHighDecisionOptionStates(risk, residualAssessment, actions);
  }

  return DECISION_OPTIONS.map((option) => ({
    ...option,
    isAvailable: false,
    reason: "Unsupported committee Authority Level.",
  }));
}

function getLowDecisionOptionStates(
  risk: RiskRecordRead,
  residualAssessment: RiskAssessmentRead | undefined,
  actions: RiskActionRead[],
): DecisionOptionState[] {
  const isOperationalBoardReview = [
    "SUBMITTED_TO_OPERATIONAL_BOARD",
    "UNDER_OPERATIONAL_BOARD_REVIEW",
  ].includes(risk.workflow_status);
  const canRejectOrReturn = !isFinalWorkflowStatus(risk.workflow_status);
  const residualBlockReason = getLowResidualBlockReason(residualAssessment);
  const closeBlockReason =
    getLowCloseBlockReason(residualAssessment, actions) ?? undefined;

  return DECISION_OPTIONS.map((option) => {
    if (option.value === "APPROVE") {
      return {
        ...option,
        isAvailable: isOperationalBoardReview,
        reason: isOperationalBoardReview
          ? undefined
          : "Risk is not awaiting operational board approval.",
      };
    }

    if (option.value === "REJECT" || option.value === "RETURN_FOR_REVISION") {
      return {
        ...option,
        isAvailable: canRejectOrReturn,
        reason: canRejectOrReturn
          ? undefined
          : "Final risk workflow states cannot be changed here.",
      };
    }

    if (option.value === "ESCALATE") {
      return {
        ...option,
        isAvailable: isOperationalBoardReview,
        reason: isOperationalBoardReview
          ? undefined
          : "Risk is not awaiting operational board escalation.",
      };
    }

    if (option.value === "ACCEPT_RESIDUAL_RISK") {
      return {
        ...option,
        isAvailable: !residualBlockReason,
        reason: residualBlockReason,
      };
    }

    return {
      ...option,
      isAvailable: !closeBlockReason,
      reason: closeBlockReason,
    };
  });
}

function getMiddleDecisionOptionStates(
  risk: RiskRecordRead,
  residualAssessment: RiskAssessmentRead | undefined,
  actions: RiskActionRead[],
): DecisionOptionState[] {
  const isRmcReview = [
    "ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE",
    "UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW",
  ].includes(risk.workflow_status);
  const canRejectOrReturn = !isFinalWorkflowStatus(risk.workflow_status);

  return DECISION_OPTIONS.map((option) => {
    if (option.value === "APPROVE" || option.value === "ESCALATE") {
      return {
        ...option,
        isAvailable: isRmcReview,
        reason: isRmcReview
          ? undefined
          : "Risk is not awaiting Risk Management Committee review.",
      };
    }

    if (option.value === "REJECT" || option.value === "RETURN_FOR_REVISION") {
      return {
        ...option,
        isAvailable: canRejectOrReturn,
        reason: canRejectOrReturn
          ? undefined
          : "Final risk workflow states cannot be changed here.",
      };
    }

    if (option.value === "ACCEPT_RESIDUAL_RISK") {
      return {
        ...option,
        isAvailable: Boolean(residualAssessment),
        reason: residualAssessment
          ? undefined
          : "Residual assessment is required before residual risk acceptance.",
      };
    }

    return {
      ...option,
      isAvailable: Boolean(residualAssessment) && !hasOpenMitigationActions(actions),
      reason: getCloseBlockReason(residualAssessment, actions),
    };
  });
}

function getHighDecisionOptionStates(
  risk: RiskRecordRead,
  residualAssessment: RiskAssessmentRead | undefined,
  actions: RiskActionRead[],
): DecisionOptionState[] {
  const isExecutiveReview = [
    "ESCALATED_TO_EXECUTIVE_COMMITTEE",
    "UNDER_EXECUTIVE_COMMITTEE_REVIEW",
  ].includes(risk.workflow_status);
  const canRejectOrReturn = !isFinalWorkflowStatus(risk.workflow_status);

  return DECISION_OPTIONS.map((option) => {
    if (option.value === "APPROVE") {
      return {
        ...option,
        isAvailable: isExecutiveReview,
        reason: isExecutiveReview
          ? undefined
          : "Risk is not awaiting Executive Committee review.",
      };
    }

    if (option.value === "REJECT" || option.value === "RETURN_FOR_REVISION") {
      return {
        ...option,
        isAvailable: canRejectOrReturn,
        reason: canRejectOrReturn
          ? undefined
          : "Final risk workflow states cannot be changed here.",
      };
    }

    if (option.value === "ESCALATE") {
      return {
        ...option,
        isAvailable: false,
        reason: "Executive authority cannot escalate further.",
      };
    }

    if (option.value === "ACCEPT_RESIDUAL_RISK") {
      return {
        ...option,
        isAvailable: Boolean(residualAssessment),
        reason: residualAssessment
          ? undefined
          : "Residual assessment is required before residual risk acceptance.",
      };
    }

    return {
      ...option,
      isAvailable: Boolean(residualAssessment) && !hasOpenMitigationActions(actions),
      reason: getCloseBlockReason(residualAssessment, actions),
    };
  });
}

function getLowResidualBlockReason(
  residualAssessment: RiskAssessmentRead | undefined,
): string | undefined {
  if (!residualAssessment) {
    return "Residual assessment is required before residual risk acceptance.";
  }

  if (residualAssessment.is_tolerable !== true) {
    return "Residual risk is not tolerable.";
  }

  if (residualAssessment.requires_escalation === true) {
    return "Residual risk requires escalation.";
  }

  return undefined;
}

function getLowCloseBlockReason(
  residualAssessment: RiskAssessmentRead | undefined,
  actions: RiskActionRead[],
): string | undefined {
  if (!residualAssessment) {
    return "Residual assessment is required before closure.";
  }

  if (residualAssessment.is_tolerable !== true) {
    return "Residual risk is not tolerable.";
  }

  if (residualAssessment.requires_escalation === true) {
    return "Residual risk requires escalation.";
  }

  if (hasOpenMitigationActions(actions)) {
    return "Open mitigation actions must be completed or cancelled before closure.";
  }

  return undefined;
}

function getCloseBlockReason(
  residualAssessment: RiskAssessmentRead | undefined,
  actions: RiskActionRead[],
): string | undefined {
  if (!residualAssessment) {
    return "Residual assessment is required before closure.";
  }

  if (hasOpenMitigationActions(actions)) {
    return "Open mitigation actions must be completed or cancelled before closure.";
  }

  return undefined;
}

function isFinalWorkflowStatus(status: string): boolean {
  return ["CLOSED", "ACCEPTED", "REJECTED"].includes(status);
}

function hasOpenMitigationActions(actions: RiskActionRead[]): boolean {
  return actions.some(isOpenMitigationAction);
}

function isOpenMitigationAction(action: RiskActionRead): boolean {
  if (action.completed_at || action.status === "COMPLETED") {
    return false;
  }

  if (action.status === "CANCELLED") {
    return false;
  }

  return true;
}

function formatOptionalBoolean(value: boolean | null | undefined): string {
  if (value === true) {
    return "Yes";
  }

  if (value === false) {
    return "No";
  }

  return "Not available";
}

function getSelectableCommittees(
  committees: CommitteeRead[],
  memberships: CommitteeMemberRead[],
): CommitteeRead[] {
  const userCommitteeIds = new Set(
    memberships
      .filter((membership) => membership.is_active)
      .map((membership) => membership.committee_id),
  );

  return committees.filter((committee) => userCommitteeIds.has(committee.id));
}

function findMembershipForCommittee(
  memberships: CommitteeMemberRead[],
  committeeId: string,
): CommitteeMemberRead | undefined {
  return memberships.find(
    (membership) => membership.is_active && membership.committee_id === committeeId,
  );
}

function getCommitteeOptionLabel(
  committee: CommitteeRead,
  membership: CommitteeMemberRead | undefined,
): string {
  const roleLabel = membership?.role_label?.trim();
  return roleLabel
    ? `${committee.name} - Authority Level: ${committee.authority_level} - ${roleLabel}`
    : `${committee.name} - Authority Level: ${committee.authority_level}`;
}
