import { apiRequest } from "./client";
import type {
  RiskLevelRead,
  RiskLikelihoodLevelRead,
  RiskMatrixCellRead,
  RiskSeverityLevelRead,
} from "./types";

type ListResponse<T> = T[] | { items?: T[] };

async function listMatrixRecords<T>(path: string, token: string): Promise<T[]> {
  const response = await apiRequest<ListResponse<T>>(path, { token });
  return Array.isArray(response) ? response : response.items ?? [];
}

export async function listSeverityLevels(
  token: string,
): Promise<RiskSeverityLevelRead[]> {
  const levels = await listMatrixRecords<RiskSeverityLevelRead>(
    "/risk-matrix/severity-levels",
    token,
  );
  return sortActiveLevels(levels);
}

export async function listLikelihoodLevels(
  token: string,
): Promise<RiskLikelihoodLevelRead[]> {
  const levels = await listMatrixRecords<RiskLikelihoodLevelRead>(
    "/risk-matrix/likelihood-levels",
    token,
  );
  return sortActiveLevels(levels);
}

export function listRiskLevels(token: string): Promise<RiskLevelRead[]> {
  return listMatrixRecords<RiskLevelRead>("/risk-matrix/risk-levels", token);
}

export function listRiskMatrixCells(token: string): Promise<RiskMatrixCellRead[]> {
  return listMatrixRecords<RiskMatrixCellRead>("/risk-matrix/cells", token);
}

function sortActiveLevels<T extends { is_active: boolean; numeric_value: number }>(
  levels: T[],
): T[] {
  return levels
    .filter((level) => level.is_active)
    .sort((first, second) => first.numeric_value - second.numeric_value);
}
