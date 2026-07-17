import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { getDataRetentionPolicy } from "../api/dataRetentionPolicy";
import type {
  DataRetentionPolicyItemRead,
  DataRetentionPolicyRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type DataRetentionPolicyState =
  | { status: "loading" }
  | { status: "success"; policy: DataRetentionPolicyRead }
  | { status: "error"; message: string };

export function DataRetentionPolicyPage() {
  const { isAuthenticated, token } = useAuth();
  const [policyState, setPolicyState] = useState<DataRetentionPolicyState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    if (!token) {
      return;
    }

    const tokenToUse = token;

    async function loadPolicy() {
      setPolicyState({ status: "loading" });
      try {
        const policy = await getDataRetentionPolicy(tokenToUse);
        if (isCurrent) {
          setPolicyState({ status: "success", policy });
        }
      } catch (error) {
        if (isCurrent) {
          setPolicyState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadPolicy();

    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  if (policyState.status === "loading") {
    return (
      <p aria-live="polite" className="workspace-status" role="status">
        Loading Retention Policy...
      </p>
    );
  }

  if (policyState.status === "error") {
    return (
      <section
        className="retention-policy-page"
        aria-labelledby="retention-policy-error"
      >
        <div aria-live="polite" className="workspace-alert" role="alert">
          <strong id="retention-policy-error">
            Unable to load Retention Policy.
          </strong>
          <span>{policyState.message}</span>
        </div>
      </section>
    );
  }

  const policy = policyState.policy;

  return (
    <section
      className="retention-policy-page"
      aria-labelledby="retention-policy-heading"
    >
      <header className="page-header">
        <div>
          <p className="eyebrow">SMS governance</p>
          <h1 id="retention-policy-heading">Data Retention</h1>
          <p>{policy.summary}</p>
        </div>
      </header>

      <section
        className="retention-policy-summary"
        aria-label="Policy summary"
      >
        <PolicySummaryItem label="Policy" value={policy.policy_name} />
        <PolicySummaryItem label="Version" value={policy.policy_version} />
        <PolicySummaryItem label="Status" value={policy.effective_status} />
        <PolicySummaryItem
          label="Generated"
          value={formatDateTime(policy.generated_at)}
        />
      </section>

      <section
        className="retention-policy-principles"
        aria-labelledby="retention-principles-heading"
      >
        <h2 id="retention-principles-heading">Archive Policy principles</h2>
        <ul>
          {policy.principles.map((principle) => (
            <li key={principle}>{principle}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="retention-matrix-heading">
        <div className="management-section-header">
          <div>
            <p className="eyebrow">Retention Period</p>
            <h2 id="retention-matrix-heading">Retention matrix</h2>
          </div>
        </div>
        <RetentionTable items={policy.items} />
      </section>

      <section className="retention-policy-warning">
        <h2>No Hard Delete</h2>
        <p>
          Governed SMS records should be archived, not hard-deleted. Audit
          Integrity and Evidence Preservation must be maintained.
        </p>
        <ul>
          {policy.no_hard_delete_record_types.map((recordType) => (
            <li key={recordType}>{recordType}</li>
          ))}
        </ul>
      </section>

      <section className="retention-policy-warning">
        <h2>Legal / Investigation Hold</h2>
        <p>
          Legal, investigation, airworthiness, or regulatory holds override
          normal retention periods and Archive Review decisions.
        </p>
        <ul>
          {policy.requires_legal_or_investigation_hold_review.map((recordType) => (
            <li key={recordType}>{recordType}</li>
          ))}
        </ul>
      </section>
    </section>
  );
}

function PolicySummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RetentionTable({ items }: { items: DataRetentionPolicyItemRead[] }) {
  return (
    <div className="retention-policy-table">
      <table>
        <thead>
          <tr>
            <th scope="col">Record Type</th>
            <th scope="col">Retention Period</th>
            <th scope="col">Archive Rule</th>
            <th scope="col">Deletion Rule</th>
            <th scope="col">Owner</th>
            <th scope="col">Notes</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.record_type}>
              <td>
                <strong>{item.record_type}</strong>
                <span>{item.description}</span>
              </td>
              <td>{item.default_retention_period}</td>
              <td>{item.archive_rule}</td>
              <td>{item.deletion_rule}</td>
              <td>{item.owner}</td>
              <td>{item.notes}</td>
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
