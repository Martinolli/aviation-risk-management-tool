import { useEffect, useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import { ApiError } from "../api/client";
import { listCommittees } from "../api/committees";
import { listRisks } from "../api/risks";
import type { CommitteeRead, RiskRecordRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RiskListState =
  | { status: "loading" }
  | {
      status: "success";
      risks: RiskRecordRead[];
      committees: CommitteeRead[];
      committeeWarning: string | null;
    }
  | { status: "error"; message: string };

export function RiskListPage() {
  const { isAuthenticated, token } = useAuth();
  const location = useLocation();
  const [riskList, setRiskList] = useState<RiskListState>({ status: "loading" });
  const successMessage = getSuccessMessage(location.state);

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadRisks() {
      const [riskResult, committeeResult] = await Promise.allSettled([
        listRisks(tokenToUse),
        listCommittees(tokenToUse),
      ]);

      if (!isCurrent) {
        return;
      }

      if (riskResult.status === "rejected") {
        setRiskList({
          status: "error",
          message:
            riskResult.reason instanceof ApiError
              ? riskResult.reason.message
              : "Please try again shortly.",
        });
        return;
      }

      setRiskList({
        status: "success",
        risks: riskResult.value,
        committees:
          committeeResult.status === "fulfilled" ? committeeResult.value : [],
        committeeWarning:
          committeeResult.status === "rejected"
            ? "Committee names could not be loaded. Board of Origin IDs are shown instead."
            : null,
      });
    }

    void loadRisks();

    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  return (
    <section className="workspace-page" aria-labelledby="risk-list-heading">
      <div className="page-header">
        <div>
          <p className="eyebrow">Risk workspace</p>
          <h1 id="risk-list-heading">Risk records</h1>
          <p>
            Review the risk records authorized for your account and their
            originating committees.
          </p>
        </div>
        <Link className="button" to="/risks/new">
          Create risk
        </Link>
      </div>

      {successMessage && (
        <p aria-live="polite" className="workspace-success" role="status">
          {successMessage}
        </p>
      )}

      {riskList.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading risk records...
        </p>
      )}

      {riskList.status === "error" && (
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong>Unable to load risk records.</strong>
          <span>{riskList.message}</span>
        </div>
      )}

      {riskList.status === "success" && riskList.committeeWarning && (
        <p className="audit-warning" role="status">
          {riskList.committeeWarning}
        </p>
      )}

      {riskList.status === "success" && riskList.risks.length === 0 && (
        <section className="workspace-empty" aria-labelledby="empty-risks-heading">
          <h2 id="empty-risks-heading">No risk records found yet.</h2>
          <p>Create the first draft risk to begin the workflow.</p>
        </section>
      )}

      {riskList.status === "success" && riskList.risks.length > 0 && (
        <div className="risk-table-wrapper">
          <table className="risk-table">
            <caption className="visually-hidden">Available risk records</caption>
            <thead>
              <tr>
                <th scope="col">Risk ID</th>
                <th scope="col">Domain</th>
                <th scope="col">Board of Origin</th>
                <th scope="col">Status</th>
                <th scope="col">Problem description</th>
                <th scope="col">Updated</th>
              </tr>
            </thead>
            <tbody>
              {riskList.risks.map((risk) => (
                <tr key={risk.id}>
                  <td className="risk-id">
                    <Link className="risk-detail-link" to={`/risks/${risk.id}`}>
                      {getRiskDisplayId(risk)}
                    </Link>
                  </td>
                  <td>{risk.domain}</td>
                  <td className="risk-board-origin">
                    {getBoardOfOriginLabel(risk, riskList.committees)}
                  </td>
                  <td>
                    <span className="status-badge">{getRiskStatus(risk)}</span>
                  </td>
                  <td className="risk-description" title={risk.problem_description}>
                    {risk.problem_description}
                  </td>
                  <td className="muted-text">{getRiskDate(risk)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

export function getRiskStatus(risk: RiskRecordRead): string {
  return risk.workflow_status || risk.lifecycle_status || "Unknown";
}

function getBoardOfOriginLabel(
  risk: RiskRecordRead,
  committees: CommitteeRead[],
): string {
  if (!risk.board_of_origin_id) {
    return "Not assigned";
  }

  return (
    committees.find((committee) => committee.id === risk.board_of_origin_id)
      ?.name ?? risk.board_of_origin_id
  );
}

function getRiskDate(risk: RiskRecordRead): string {
  const date = new Date(risk.updated_at || risk.created_at);

  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString();
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
