import type { AuditLogRead } from "../api/types";

interface AuditLogListProps {
  auditLogs: AuditLogRead[];
}

export function AuditLogList({ auditLogs }: AuditLogListProps) {
  return (
    <ul className="audit-log-list">
      {auditLogs.map((auditLog) => {
        const showValues =
          Boolean(auditLog.field_name) ||
          hasMeaningfulAuditValue(auditLog.old_value) ||
          hasMeaningfulAuditValue(auditLog.new_value);

        return (
          <li className="audit-log-item" key={auditLog.id}>
            <div className="audit-log-header">
              <span className="audit-action-badge">
                {formatAuditAction(auditLog.action)}
              </span>
              <strong className="audit-entity">
                {formatAuditEntity(auditLog.entity_type, auditLog.field_name)}
              </strong>
            </div>

            <dl className="audit-meta">
              <div>
                <dt>Changed</dt>
                <dd>{formatDateTime(auditLog.changed_at)}</dd>
              </div>
              <div>
                <dt>Changed by</dt>
                <dd>{auditLog.changed_by_user_id || "Not recorded"}</dd>
              </div>
            </dl>

            {auditLog.reason && (
              <p className="audit-reason">
                <strong>Reason:</strong> {auditLog.reason}
              </p>
            )}

            {showValues && (
              <div className="audit-values">
                <div className="audit-value-block">
                  <strong>Old</strong>
                  <pre>{formatAuditValue(auditLog.old_value)}</pre>
                </div>
                <div className="audit-value-block">
                  <strong>New</strong>
                  <pre>{formatAuditValue(auditLog.new_value)}</pre>
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function formatAuditAction(action: string): string {
  return action.replace(/_/g, " ") || "AUDIT EVENT";
}

function formatAuditEntity(
  entityType: string,
  fieldName: string | null | undefined,
): string {
  return fieldName ? `${entityType}.${fieldName}` : entityType;
}

function hasMeaningfulAuditValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}

function formatAuditValue(value: unknown): string {
  if (!hasMeaningfulAuditValue(value)) {
    return "Not recorded";
  }

  if (typeof value === "object") {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  return String(value);
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not available" : date.toLocaleString();
}
