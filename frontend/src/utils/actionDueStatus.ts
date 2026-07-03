import type { RiskActionRead } from "../api/types";

export type RiskActionDueStatus =
  | "OVERDUE"
  | "DUE_TODAY"
  | "DUE_SOON"
  | "OPEN"
  | "NO_DUE_DATE"
  | "COMPLETED"
  | "CANCELLED";

const DAY_IN_MILLISECONDS = 24 * 60 * 60 * 1000;

const DUE_STATUS_PRIORITY: Record<RiskActionDueStatus, number> = {
  OVERDUE: 0,
  DUE_TODAY: 1,
  DUE_SOON: 2,
  OPEN: 3,
  NO_DUE_DATE: 4,
  COMPLETED: 5,
  CANCELLED: 6,
};

export function getRiskActionDueStatus(
  action: RiskActionRead,
  today = new Date(),
): RiskActionDueStatus {
  if (action.status === "COMPLETED") {
    return "COMPLETED";
  }
  if (action.status === "CANCELLED") {
    return "CANCELLED";
  }
  if (!action.due_date) {
    return "NO_DUE_DATE";
  }

  const dueDay = parseDateOnly(action.due_date);
  if (dueDay === null) {
    return "OPEN";
  }
  const todayDay = Date.UTC(
    today.getFullYear(),
    today.getMonth(),
    today.getDate(),
  );
  const daysUntilDue = Math.round((dueDay - todayDay) / DAY_IN_MILLISECONDS);

  if (daysUntilDue < 0) {
    return "OVERDUE";
  }
  if (daysUntilDue === 0) {
    return "DUE_TODAY";
  }
  if (daysUntilDue <= 7) {
    return "DUE_SOON";
  }
  return "OPEN";
}

export function getRiskActionDueStatusLabel(
  status: RiskActionDueStatus,
): string {
  const labels: Record<RiskActionDueStatus, string> = {
    OVERDUE: "Overdue",
    DUE_TODAY: "Due Today",
    DUE_SOON: "Due Soon",
    OPEN: "Open",
    NO_DUE_DATE: "No Due Date",
    COMPLETED: "Completed",
    CANCELLED: "Cancelled",
  };
  return labels[status];
}

export function getRiskActionDueStatusTone(
  status: RiskActionDueStatus,
): string {
  return status.toLowerCase().replace(/_/g, "-");
}

export function compareRiskActionsByUrgency(
  first: RiskActionRead,
  second: RiskActionRead,
): number {
  const statusDifference =
    DUE_STATUS_PRIORITY[getRiskActionDueStatus(first)] -
    DUE_STATUS_PRIORITY[getRiskActionDueStatus(second)];
  if (statusDifference !== 0) {
    return statusDifference;
  }

  const dueDateDifference = compareDates(first.due_date, second.due_date);
  if (dueDateDifference !== 0) {
    return dueDateDifference;
  }

  return parseTimestamp(second.created_at) - parseTimestamp(first.created_at);
}

export function isRiskActionOpen(action: RiskActionRead): boolean {
  return action.status !== "COMPLETED" && action.status !== "CANCELLED";
}

function parseDateOnly(value: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) {
    return null;
  }
  const parsed = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(parsed) ? null : parsed;
}

function compareDates(
  first: string | null | undefined,
  second: string | null | undefined,
): number {
  if (!first && !second) {
    return 0;
  }
  if (!first) {
    return 1;
  }
  if (!second) {
    return -1;
  }
  return first.localeCompare(second);
}

function parseTimestamp(value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}
