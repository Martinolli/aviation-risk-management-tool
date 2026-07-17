import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { getPermissionMatrix } from "../api/permissionMatrix";
import type {
  PermissionMatrixRead,
  PermissionMatrixRuleRead,
  PermissionMatrixSectionRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type PermissionMatrixState =
  | { status: "loading" }
  | { status: "success"; matrix: PermissionMatrixRead }
  | { status: "error"; message: string };

const HIGHLIGHT_TERMS = [
  "Authority Level",
  "Board of Origin",
  "No Hard Delete / Archive Restore",
  "Export authorization boundary",
];

export function PermissionMatrixPage() {
  const { isAuthenticated, token } = useAuth();
  const [matrixState, setMatrixState] = useState<PermissionMatrixState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadMatrix() {
      setMatrixState({ status: "loading" });
      try {
        const matrix = await getPermissionMatrix(tokenToUse);
        if (isCurrent) {
          setMatrixState({ status: "success", matrix });
        }
      } catch (error) {
        if (isCurrent) {
          setMatrixState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadMatrix();

    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (matrixState.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading Permission Matrix...
      </p>
    );
  }

  if (matrixState.status === "error") {
    return (
      <section
        className="permission-matrix-page"
        aria-labelledby="permission-matrix-error"
      >
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="permission-matrix-error">
            Unable to load Permission Matrix.
          </strong>
          <span>{matrixState.message}</span>
        </div>
      </section>
    );
  }

  const matrix = matrixState.matrix;

  return (
    <section
      className="permission-matrix-page"
      aria-labelledby="permission-matrix-heading"
    >
      <header className="page-header">
        <div>
          <p className="eyebrow">SMS governance</p>
          <h1 id="permission-matrix-heading">Permission Matrix</h1>
          <p>{matrix.summary}</p>
        </div>
      </header>

      <section
        className="permission-matrix-summary"
        aria-label="Permission matrix summary"
      >
        <SummaryItem label="Policy" value={matrix.policy_name} />
        <SummaryItem label="Version" value={matrix.policy_version} />
        <SummaryItem label="Status" value={matrix.effective_status} />
        <SummaryItem
          label="Generated"
          value={formatDateTime(matrix.generated_at)}
        />
      </section>

      <section
        className="permission-matrix-principles"
        aria-labelledby="permission-principles-heading"
      >
        <h2 id="permission-principles-heading">Access Control principles</h2>
        <ul>
          {matrix.principles.map((principle) => (
            <li key={principle}>{principle}</li>
          ))}
        </ul>
      </section>

      <section className="permission-matrix-warning">
        <h2>Governance review focus</h2>
        <div>
          {HIGHLIGHT_TERMS.map((term) => (
            <span className="permission-matrix-badge" key={term}>
              {term}
            </span>
          ))}
        </div>
      </section>

      {matrix.sections.map((section) => (
        <PermissionSection key={section.section} section={section} />
      ))}
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function PermissionSection({
  section,
}: {
  section: PermissionMatrixSectionRead;
}) {
  return (
    <section
      className="permission-matrix-section"
      aria-labelledby={`permission-${slugify(section.section)}`}
    >
      <div className="management-section-header">
        <div>
          <p className="eyebrow">Access Control</p>
          <h2 id={`permission-${slugify(section.section)}`}>{section.section}</h2>
          <p>{section.description}</p>
        </div>
      </div>
      <PermissionTable rules={section.rules} />
    </section>
  );
}

function PermissionTable({ rules }: { rules: PermissionMatrixRuleRead[] }) {
  return (
    <div className="permission-matrix-table">
      <table>
        <thead>
          <tr>
            <th scope="col">Capability</th>
            <th scope="col">Allowed Users / Roles</th>
            <th scope="col">Authority Level</th>
            <th scope="col">Access Basis</th>
            <th scope="col">Restrictions</th>
            <th scope="col">Audit Expected</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((rule) => (
            <tr key={`${rule.area}:${rule.capability}`}>
              <td>
                <strong>{rule.capability}</strong>
                {rule.notes && <span>{rule.notes}</span>}
              </td>
              <td>
                <ul>
                  {rule.allowed_roles_or_users.map((allowed) => (
                    <li key={allowed}>{allowed}</li>
                  ))}
                </ul>
              </td>
              <td>{rule.authority_level || "N/A"}</td>
              <td>{rule.access_basis}</td>
              <td>{rule.restrictions}</td>
              <td>
                <span
                  className={`permission-matrix-badge ${
                    rule.audit_expected ? "audit-yes" : "audit-no"
                  }`}
                >
                  {rule.audit_expected ? "Yes" : "No"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not available" : date.toLocaleString();
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
