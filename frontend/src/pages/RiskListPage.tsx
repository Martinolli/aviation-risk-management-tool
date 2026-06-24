import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { listRisks } from "../api/risks";
import type { RiskRecordRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type RiskListState =
  | { status: "loading" }
  | { status: "success"; risks: RiskRecordRead[] }
  | { status: "error"; message: string };

export function RiskListPage() {
  const { isAuthenticated, token } = useAuth();
  const [riskList, setRiskList] = useState<RiskListState>({ status: "loading" });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadRisks() {
      try {
        const risks = await listRisks(tokenToUse);
        if (isCurrent) {
          setRiskList({ status: "success", risks });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setRiskList({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
      }
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
            Review the risk records currently available in the safety management
            system.
          </p>
        </div>
        <button className="button button--coming-soon" disabled type="button">
          Create risk
        </button>
      </div>

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

      {riskList.status === "success" && riskList.risks.length === 0 && (
        <section className="workspace-empty" aria-labelledby="empty-risks-heading">
          <h2 id="empty-risks-heading">No risk records found yet.</h2>
          <p>Risk creation will be added in the next task.</p>
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
                <th scope="col">Status</th>
                <th scope="col">Problem description</th>
                <th scope="col">Updated</th>
              </tr>
            </thead>
            <tbody>
              {riskList.risks.map((risk) => (
                <tr key={risk.id}>
                  <td className="risk-id">{getRiskDisplayId(risk)}</td>
                  <td>{risk.domain}</td>
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

function getRiskDate(risk: RiskRecordRead): string {
  const date = new Date(risk.updated_at || risk.created_at);

  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString();
}
