import { apiRequest } from "./client";
import type {
  CommitteeMeetingAttendeeCreateRequest,
  CommitteeMeetingCancelRequest,
  CommitteeMeetingCreateRequest,
  CommitteeMeetingFinalizeRequest,
  CommitteeMeetingRead,
  CommitteeMeetingRiskItemCreateRequest,
  CommitteeMeetingRiskItemUpdateRequest,
  CommitteeMeetingStatus,
  CommitteeMeetingUpdateRequest,
} from "./types";

interface ListCommitteeMeetingsParams {
  committeeId?: string;
  status?: CommitteeMeetingStatus | "";
}

export function listCommitteeMeetings(
  token: string,
  params: ListCommitteeMeetingsParams = {},
): Promise<CommitteeMeetingRead[]> {
  const query = new URLSearchParams();
  if (params.committeeId) {
    query.set("committee_id", params.committeeId);
  }
  if (params.status) {
    query.set("status", params.status);
  }
  const queryString = query.toString();
  return apiRequest<CommitteeMeetingRead[]>(
    queryString ? `/committee-meetings?${queryString}` : "/committee-meetings",
    { token },
  );
}

export function createCommitteeMeeting(
  token: string,
  request: CommitteeMeetingCreateRequest,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>("/committee-meetings", {
    method: "POST",
    token,
    body: request,
  });
}

export function getCommitteeMeeting(
  token: string,
  meetingId: string,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(meetingId)}`,
    { token },
  );
}

export function updateCommitteeMeeting(
  token: string,
  meetingId: string,
  request: CommitteeMeetingUpdateRequest,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(meetingId)}`,
    {
      method: "PATCH",
      token,
      body: request,
    },
  );
}

export function finalizeCommitteeMeeting(
  token: string,
  meetingId: string,
  request: CommitteeMeetingFinalizeRequest,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(meetingId)}/finalize`,
    {
      method: "POST",
      token,
      body: request,
    },
  );
}

export function cancelCommitteeMeeting(
  token: string,
  meetingId: string,
  request: CommitteeMeetingCancelRequest,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(meetingId)}/cancel`,
    {
      method: "POST",
      token,
      body: request,
    },
  );
}

export function addCommitteeMeetingAttendee(
  token: string,
  meetingId: string,
  request: CommitteeMeetingAttendeeCreateRequest,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(meetingId)}/attendees`,
    {
      method: "POST",
      token,
      body: request,
    },
  );
}

export function updateCommitteeMeetingAttendee(
  token: string,
  meetingId: string,
  attendeeId: string,
  request: CommitteeMeetingAttendeeCreateRequest,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(
      meetingId,
    )}/attendees/${encodeURIComponent(attendeeId)}`,
    {
      method: "PATCH",
      token,
      body: request,
    },
  );
}

export function removeCommitteeMeetingAttendee(
  token: string,
  meetingId: string,
  attendeeId: string,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(
      meetingId,
    )}/attendees/${encodeURIComponent(attendeeId)}`,
    {
      method: "DELETE",
      token,
    },
  );
}

export function addCommitteeMeetingRiskItem(
  token: string,
  meetingId: string,
  request: CommitteeMeetingRiskItemCreateRequest,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(meetingId)}/risk-items`,
    {
      method: "POST",
      token,
      body: request,
    },
  );
}

export function updateCommitteeMeetingRiskItem(
  token: string,
  meetingId: string,
  riskItemId: string,
  request: CommitteeMeetingRiskItemUpdateRequest,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(
      meetingId,
    )}/risk-items/${encodeURIComponent(riskItemId)}`,
    {
      method: "PATCH",
      token,
      body: request,
    },
  );
}

export function removeCommitteeMeetingRiskItem(
  token: string,
  meetingId: string,
  riskItemId: string,
): Promise<CommitteeMeetingRead> {
  return apiRequest<CommitteeMeetingRead>(
    `/committee-meetings/${encodeURIComponent(
      meetingId,
    )}/risk-items/${encodeURIComponent(riskItemId)}`,
    {
      method: "DELETE",
      token,
    },
  );
}
