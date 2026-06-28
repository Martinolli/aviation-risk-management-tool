import { apiRequest } from "./client";
import type { MyDecisionQueueRead } from "./types";

export function getMyDecisionQueue(token: string): Promise<MyDecisionQueueRead> {
  return apiRequest<MyDecisionQueueRead>("/decision-queue/my", { token });
}
