import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { listAuditLogs } from "../api/auditLogs";
import { ApiError } from "../api/client";
import type { AuditLogRead } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { AuditLogList } from "../components/AuditLogList";

type AuditTrailPageState =
  | { status: "loading" }
  | { status: "success"; auditLogs: AuditLogRead[] }
  | { status: "error"; message: string };

export function AuditTrailPage() {
  const { isAuthenticated, token } = useAuth();
  const [auditTrailState, setAuditTrailState] = useState<AuditTrailPageState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadAuditTrail() {
      try {
        const auditLogs = await listAuditLogs(tokenToUse, { limit: 100 });
        if (isCurrent) {
          setAuditTrailState({ status: "success", auditLogs });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setAuditTrailState({
          status: "error",
          message:
            error instanceof ApiError
              ? error.message
              : "Please try again shortly.",
        });
      }
    }

    void loadAuditTrail();

    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  return (
    <section className="audit-trail-page" aria-labelledby="audit-trail-heading">
      <div className="page-header">
        <div>
          <p className="eyebrow">Traceability</p>
          <h1 id="audit-trail-heading">Audit Trail</h1>
          <p>
            Review the latest audit records authorized for your account.
          </p>
        </div>
      </div>

      {auditTrailState.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading audit trail...
        </p>
      )}

      {auditTrailState.status === "error" && (
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong>Unable to load audit trail.</strong>
          <span>{auditTrailState.message}</span>
        </div>
      )}

      {auditTrailState.status === "success" &&
        auditTrailState.auditLogs.length === 0 && (
          <p className="audit-empty">No authorized audit records available.</p>
        )}

      {auditTrailState.status === "success" &&
        auditTrailState.auditLogs.length > 0 && (
          <AuditLogList auditLogs={auditTrailState.auditLogs} />
        )}
    </section>
  );
}
