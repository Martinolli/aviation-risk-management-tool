import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  addCommitteeMeetingAttendee,
  addCommitteeMeetingRiskItem,
  cancelCommitteeMeeting,
  finalizeCommitteeMeeting,
  getCommitteeMeeting,
  removeCommitteeMeetingAttendee,
  removeCommitteeMeetingRiskItem,
  updateCommitteeMeeting,
  updateCommitteeMeetingAttendee,
  updateCommitteeMeetingRiskItem,
} from "../api/committeeMeetings";
import {
  downloadGeneratedReport,
  generateCommitteeMeetingMinutesReport,
  saveBlobAsFile,
} from "../api/reports";
import type {
  CommitteeMeetingAttendanceStatus,
  CommitteeMeetingRead,
  GeneratedReportRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type DetailState =
  | { status: "loading" }
  | { status: "success"; meeting: CommitteeMeetingRead }
  | { status: "error"; message: string };

export function CommitteeMeetingDetailPage() {
  const { meetingId } = useParams();
  const { isAuthenticated, token } = useAuth();
  const [detailState, setDetailState] = useState<DetailState>({
    status: "loading",
  });
  const [editForm, setEditForm] = useState({
    title: "",
    meeting_date: "",
    location: "",
    chair_user_id: "",
    agenda_summary: "",
    discussion_summary: "",
    decisions_summary: "",
    action_items_summary: "",
  });
  const [attendeeForm, setAttendeeForm] = useState({
    user_id: "",
    attendee_name: "",
    attendee_email: "",
    role_label: "",
    attendance_status: "PRESENT" as CommitteeMeetingAttendanceStatus,
    notes: "",
  });
  const [riskItemForm, setRiskItemForm] = useState({
    risk_record_id: "",
    agenda_item_number: "",
    discussion_summary: "",
    decision_summary: "",
    action_items: "",
    linked_risk_decision_id: "",
    follow_up_required: false,
    follow_up_notes: "",
  });
  const [finalizationNotes, setFinalizationNotes] = useState("");
  const [cancellationReason, setCancellationReason] = useState("");
  const [generatedReport, setGeneratedReport] =
    useState<GeneratedReportRead | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    let isCurrent = true;
    if (!token || !meetingId) {
      return;
    }
    const tokenToUse = token;
    const meetingIdToUse = meetingId;

    async function loadMeeting() {
      setDetailState({ status: "loading" });
      try {
        const meeting = await getCommitteeMeeting(tokenToUse, meetingIdToUse);
        if (!isCurrent) {
          return;
        }
        setDetailState({ status: "success", meeting });
        setEditForm({
          title: meeting.title,
          meeting_date: meeting.meeting_date,
          location: meeting.location ?? "",
          chair_user_id: meeting.chair_user_id ?? "",
          agenda_summary: meeting.agenda_summary ?? "",
          discussion_summary: meeting.discussion_summary ?? "",
          decisions_summary: meeting.decisions_summary ?? "",
          action_items_summary: meeting.action_items_summary ?? "",
        });
      } catch (error) {
        if (isCurrent) {
          setDetailState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Unable to load Meeting Minutes.",
          });
        }
      }
    }

    void loadMeeting();
    return () => {
      isCurrent = false;
    };
  }, [token, meetingId]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }
  const authToken = token;

  const meeting = detailState.status === "success" ? detailState.meeting : null;
  const isDraft = meeting?.status === "DRAFT";

  function setMeeting(next: CommitteeMeetingRead) {
    setDetailState({ status: "success", meeting: next });
    setGeneratedReport(null);
  }

  async function runOperation(operation: () => Promise<void>) {
    setIsBusy(true);
    setOperationError(null);
    try {
      await operation();
    } catch (error) {
      setOperationError(
        error instanceof ApiError ? error.message : "Unable to update Meeting Minutes.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSaveMeeting(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!meeting || !meetingId) {
      return;
    }
    const meetingIdToUse = meetingId;
    await runOperation(async () => {
      const updated = await updateCommitteeMeeting(authToken, meetingIdToUse, {
        title: editForm.title.trim(),
        meeting_date: editForm.meeting_date,
        location: editForm.location.trim() || null,
        chair_user_id: editForm.chair_user_id.trim() || null,
        agenda_summary: editForm.agenda_summary.trim() || null,
        discussion_summary: editForm.discussion_summary.trim() || null,
        decisions_summary: editForm.decisions_summary.trim() || null,
        action_items_summary: editForm.action_items_summary.trim() || null,
      });
      setMeeting(updated);
    });
  }

  async function handleAddAttendee(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!meetingId) {
      return;
    }
    const meetingIdToUse = meetingId;
    await runOperation(async () => {
      const updated = await addCommitteeMeetingAttendee(authToken, meetingIdToUse, {
        user_id: attendeeForm.user_id.trim() || null,
        attendee_name: attendeeForm.attendee_name.trim() || null,
        attendee_email: attendeeForm.attendee_email.trim() || null,
        role_label: attendeeForm.role_label.trim() || null,
        attendance_status: attendeeForm.attendance_status,
        notes: attendeeForm.notes.trim() || null,
      });
      setMeeting(updated);
      setAttendeeForm({
        user_id: "",
        attendee_name: "",
        attendee_email: "",
        role_label: "",
        attendance_status: "PRESENT",
        notes: "",
      });
    });
  }

  async function handleAddRiskItem(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!meetingId) {
      return;
    }
    const meetingIdToUse = meetingId;
    await runOperation(async () => {
      const updated = await addCommitteeMeetingRiskItem(authToken, meetingIdToUse, {
        risk_record_id: riskItemForm.risk_record_id.trim(),
        agenda_item_number: riskItemForm.agenda_item_number
          ? Number(riskItemForm.agenda_item_number)
          : null,
        discussion_summary: riskItemForm.discussion_summary.trim() || null,
        decision_summary: riskItemForm.decision_summary.trim() || null,
        action_items: riskItemForm.action_items.trim() || null,
        linked_risk_decision_id: riskItemForm.linked_risk_decision_id.trim() || null,
        follow_up_required: riskItemForm.follow_up_required,
        follow_up_notes: riskItemForm.follow_up_notes.trim() || null,
      });
      setMeeting(updated);
      setRiskItemForm({
        risk_record_id: "",
        agenda_item_number: "",
        discussion_summary: "",
        decision_summary: "",
        action_items: "",
        linked_risk_decision_id: "",
        follow_up_required: false,
        follow_up_notes: "",
      });
    });
  }

  async function handleGenerateReport() {
    if (!meetingId) {
      return;
    }
    const meetingIdToUse = meetingId;
    await runOperation(async () => {
      const report = await generateCommitteeMeetingMinutesReport(
        authToken,
        meetingIdToUse,
      );
      setGeneratedReport(report);
    });
  }

  async function handleDownloadReport() {
    if (!generatedReport) {
      return;
    }
    await runOperation(async () => {
      const { blob, filename } = await downloadGeneratedReport(
        authToken,
        generatedReport.id,
      );
      saveBlobAsFile(blob, filename);
    });
  }

  if (!meetingId) {
    return <Navigate replace to="/committee-meetings" />;
  }

  return (
    <section className="committee-meeting-detail" aria-labelledby="meeting-heading">
      <Link to="/committee-meetings">Back to Meetings</Link>

      {detailState.status === "loading" && (
        <p className="workspace-status" role="status">
          Loading Meeting Minutes...
        </p>
      )}
      {detailState.status === "error" && (
        <p className="meeting-warning" role="alert">
          {detailState.message}
        </p>
      )}

      {meeting && (
        <>
          <header className="page-header">
            <div>
              <p className="eyebrow">Committee Meeting Minutes</p>
              <h1 id="meeting-heading">{meeting.title}</h1>
              <p>
                {meeting.committee_name || meeting.committee_id} - Authority Level:{" "}
                {formatLabel(meeting.authority_level)}
              </p>
            </div>
            <span className={`meeting-status-badge ${meeting.status.toLowerCase()}`}>
              {meeting.status}
            </span>
          </header>

          {operationError && (
            <p className="meeting-warning" role="alert">
              {operationError}
            </p>
          )}

          {!isDraft && (
            <p className="meeting-warning" role="status">
              Finalized or cancelled Meeting Minutes are read-only.
            </p>
          )}

          <section className="meeting-section" aria-labelledby="metadata-heading">
            <h2 id="metadata-heading">Meeting Metadata</h2>
            <dl className="meeting-metadata">
              <div>
                <dt>Committee Type</dt>
                <dd>{formatLabel(meeting.committee_type)}</dd>
              </div>
              <div>
                <dt>Meeting Date</dt>
                <dd>{formatDate(meeting.meeting_date)}</dd>
              </div>
              <div>
                <dt>Location</dt>
                <dd>{meeting.location || "Not recorded"}</dd>
              </div>
              <div>
                <dt>Chair</dt>
                <dd>{meeting.chair_user_id || "Not recorded"}</dd>
              </div>
              <div>
                <dt>Finalized</dt>
                <dd>{meeting.finalized_at ? formatDateTime(meeting.finalized_at) : "No"}</dd>
              </div>
            </dl>

            <form className="meeting-form-grid" onSubmit={handleSaveMeeting}>
              <label>
                Title
                <input
                  disabled={!isDraft}
                  onChange={(event) =>
                    setEditForm((current) => ({
                      ...current,
                      title: event.target.value,
                    }))
                  }
                  required
                  value={editForm.title}
                />
              </label>
              <label>
                Meeting date
                <input
                  disabled={!isDraft}
                  onChange={(event) =>
                    setEditForm((current) => ({
                      ...current,
                      meeting_date: event.target.value,
                    }))
                  }
                  required
                  type="date"
                  value={editForm.meeting_date}
                />
              </label>
              <label>
                Location
                <input
                  disabled={!isDraft}
                  onChange={(event) =>
                    setEditForm((current) => ({
                      ...current,
                      location: event.target.value,
                    }))
                  }
                  value={editForm.location}
                />
              </label>
              <label>
                Chair user ID
                <input
                  disabled={!isDraft}
                  onChange={(event) =>
                    setEditForm((current) => ({
                      ...current,
                      chair_user_id: event.target.value,
                    }))
                  }
                  value={editForm.chair_user_id}
                />
              </label>
              <label>
                Agenda summary
                <textarea
                  disabled={!isDraft}
                  onChange={(event) =>
                    setEditForm((current) => ({
                      ...current,
                      agenda_summary: event.target.value,
                    }))
                  }
                  rows={3}
                  value={editForm.agenda_summary}
                />
              </label>
              <label>
                General discussion
                <textarea
                  disabled={!isDraft}
                  onChange={(event) =>
                    setEditForm((current) => ({
                      ...current,
                      discussion_summary: event.target.value,
                    }))
                  }
                  rows={3}
                  value={editForm.discussion_summary}
                />
              </label>
              <label>
                Decisions summary
                <textarea
                  disabled={!isDraft}
                  onChange={(event) =>
                    setEditForm((current) => ({
                      ...current,
                      decisions_summary: event.target.value,
                    }))
                  }
                  rows={3}
                  value={editForm.decisions_summary}
                />
              </label>
              <label>
                Action items summary
                <textarea
                  disabled={!isDraft}
                  onChange={(event) =>
                    setEditForm((current) => ({
                      ...current,
                      action_items_summary: event.target.value,
                    }))
                  }
                  rows={3}
                  value={editForm.action_items_summary}
                />
              </label>
              {isDraft && (
                <div className="meeting-actions">
                  <button disabled={isBusy} type="submit">
                    Save Meeting
                  </button>
                </div>
              )}
            </form>
          </section>

          <section className="meeting-section" aria-labelledby="attendance-heading">
            <h2 id="attendance-heading">Attendance</h2>
            {isDraft && (
              <form className="meeting-form-grid" onSubmit={handleAddAttendee}>
                <label>
                  User ID
                  <input
                    onChange={(event) =>
                      setAttendeeForm((current) => ({
                        ...current,
                        user_id: event.target.value,
                      }))
                    }
                    value={attendeeForm.user_id}
                  />
                </label>
                <label>
                  Attendee name
                  <input
                    onChange={(event) =>
                      setAttendeeForm((current) => ({
                        ...current,
                        attendee_name: event.target.value,
                      }))
                    }
                    value={attendeeForm.attendee_name}
                  />
                </label>
                <label>
                  Email
                  <input
                    onChange={(event) =>
                      setAttendeeForm((current) => ({
                        ...current,
                        attendee_email: event.target.value,
                      }))
                    }
                    type="email"
                    value={attendeeForm.attendee_email}
                  />
                </label>
                <label>
                  Role
                  <input
                    onChange={(event) =>
                      setAttendeeForm((current) => ({
                        ...current,
                        role_label: event.target.value,
                      }))
                    }
                    value={attendeeForm.role_label}
                  />
                </label>
                <label>
                  Attendance Status
                  <select
                    onChange={(event) =>
                      setAttendeeForm((current) => ({
                        ...current,
                        attendance_status: event.target
                          .value as CommitteeMeetingAttendanceStatus,
                      }))
                    }
                    value={attendeeForm.attendance_status}
                  >
                    <option value="PRESENT">PRESENT</option>
                    <option value="ABSENT">ABSENT</option>
                    <option value="APOLOGY">APOLOGY</option>
                    <option value="OBSERVER">OBSERVER</option>
                  </select>
                </label>
                <label>
                  Notes
                  <textarea
                    onChange={(event) =>
                      setAttendeeForm((current) => ({
                        ...current,
                        notes: event.target.value,
                      }))
                    }
                    rows={2}
                    value={attendeeForm.notes}
                  />
                </label>
                <div className="meeting-actions">
                  <button disabled={isBusy} type="submit">
                    Add Attendance
                  </button>
                </div>
              </form>
            )}
            <div className="table-scroll">
              <table className="attendance-table">
                <thead>
                  <tr>
                    <th>Name / User ID</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Attendance Status</th>
                    <th>Notes</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {meeting.attendees.map((attendee) => (
                    <tr key={attendee.id}>
                      <td>{attendee.attendee_name || attendee.user_id}</td>
                      <td>{attendee.attendee_email || "Not recorded"}</td>
                      <td>{attendee.role_label || "Not recorded"}</td>
                      <td>{attendee.attendance_status}</td>
                      <td>{attendee.notes || "Not recorded"}</td>
                      <td>
                        {isDraft && (
                          <div className="meeting-actions">
                            <button
                              disabled={isBusy}
                              onClick={() =>
                                void runOperation(async () => {
                                  const updated =
                                    await updateCommitteeMeetingAttendee(
                                      authToken,
                                      meeting.id,
                                      attendee.id,
                                      { attendance_status: "PRESENT" },
                                    );
                                  setMeeting(updated);
                                })
                              }
                              type="button"
                            >
                              Mark Present
                            </button>
                            <button
                              disabled={isBusy}
                              onClick={() =>
                                void runOperation(async () => {
                                  const updated =
                                    await removeCommitteeMeetingAttendee(
                                      authToken,
                                      meeting.id,
                                      attendee.id,
                                    );
                                  setMeeting(updated);
                                })
                              }
                              type="button"
                            >
                              Remove
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {meeting.attendees.length === 0 && (
                    <tr>
                      <td colSpan={6}>No Attendance recorded.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="meeting-section" aria-labelledby="risk-items-heading">
            <h2 id="risk-items-heading">Risk Agenda Items</h2>
            {isDraft && (
              <form className="meeting-form-grid" onSubmit={handleAddRiskItem}>
                <label>
                  Risk record ID
                  <input
                    onChange={(event) =>
                      setRiskItemForm((current) => ({
                        ...current,
                        risk_record_id: event.target.value,
                      }))
                    }
                    required
                    value={riskItemForm.risk_record_id}
                  />
                </label>
                <label>
                  Agenda item number
                  <input
                    min="1"
                    onChange={(event) =>
                      setRiskItemForm((current) => ({
                        ...current,
                        agenda_item_number: event.target.value,
                      }))
                    }
                    type="number"
                    value={riskItemForm.agenda_item_number}
                  />
                </label>
                <label>
                  Linked Decision Record
                  <input
                    onChange={(event) =>
                      setRiskItemForm((current) => ({
                        ...current,
                        linked_risk_decision_id: event.target.value,
                      }))
                    }
                    value={riskItemForm.linked_risk_decision_id}
                  />
                </label>
                <label>
                  Discussion summary
                  <textarea
                    onChange={(event) =>
                      setRiskItemForm((current) => ({
                        ...current,
                        discussion_summary: event.target.value,
                      }))
                    }
                    rows={3}
                    value={riskItemForm.discussion_summary}
                  />
                </label>
                <label>
                  Decision summary
                  <textarea
                    onChange={(event) =>
                      setRiskItemForm((current) => ({
                        ...current,
                        decision_summary: event.target.value,
                      }))
                    }
                    rows={3}
                    value={riskItemForm.decision_summary}
                  />
                </label>
                <label>
                  Action items
                  <textarea
                    onChange={(event) =>
                      setRiskItemForm((current) => ({
                        ...current,
                        action_items: event.target.value,
                      }))
                    }
                    rows={3}
                    value={riskItemForm.action_items}
                  />
                </label>
                <label>
                  Follow-up notes
                  <textarea
                    onChange={(event) =>
                      setRiskItemForm((current) => ({
                        ...current,
                        follow_up_notes: event.target.value,
                      }))
                    }
                    rows={2}
                    value={riskItemForm.follow_up_notes}
                  />
                </label>
                <label className="meeting-checkbox">
                  <input
                    checked={riskItemForm.follow_up_required}
                    onChange={(event) =>
                      setRiskItemForm((current) => ({
                        ...current,
                        follow_up_required: event.target.checked,
                      }))
                    }
                    type="checkbox"
                  />
                  Follow-up required
                </label>
                <div className="meeting-actions">
                  <button disabled={isBusy} type="submit">
                    Add Agenda Item
                  </button>
                </div>
              </form>
            )}
            <div className="table-scroll">
              <table className="risk-agenda-table">
                <thead>
                  <tr>
                    <th>Agenda Item</th>
                    <th>Risk ID</th>
                    <th>Domain</th>
                    <th>Workflow Status</th>
                    <th>Problem Description</th>
                    <th>Decision Summary</th>
                    <th>Follow-up Required</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {meeting.risk_items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.agenda_item_number ?? "Not recorded"}</td>
                      <td>{item.risk_id || item.risk_record_id}</td>
                      <td>{formatLabel(item.risk_domain)}</td>
                      <td>{formatLabel(item.risk_workflow_status)}</td>
                      <td>{item.risk_problem_description || "Not recorded"}</td>
                      <td>{item.decision_summary || "Not recorded"}</td>
                      <td>{item.follow_up_required ? "Yes" : "No"}</td>
                      <td>
                        {isDraft && (
                          <div className="meeting-actions">
                            <button
                              disabled={isBusy}
                              onClick={() =>
                                void runOperation(async () => {
                                  const updated =
                                    await updateCommitteeMeetingRiskItem(
                                      authToken,
                                      meeting.id,
                                      item.id,
                                      { follow_up_required: true },
                                    );
                                  setMeeting(updated);
                                })
                              }
                              type="button"
                            >
                              Require Follow-up
                            </button>
                            <button
                              disabled={isBusy}
                              onClick={() =>
                                void runOperation(async () => {
                                  const updated =
                                    await removeCommitteeMeetingRiskItem(
                                      authToken,
                                      meeting.id,
                                      item.id,
                                    );
                                  setMeeting(updated);
                                })
                              }
                              type="button"
                            >
                              Remove
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {meeting.risk_items.length === 0 && (
                    <tr>
                      <td colSpan={8}>No Risk Agenda Items recorded.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="meeting-section" aria-labelledby="actions-heading">
            <h2 id="actions-heading">Meeting Actions</h2>
            {isDraft && (
              <div className="meeting-form-grid">
                <label>
                  Finalization notes
                  <textarea
                    onChange={(event) => setFinalizationNotes(event.target.value)}
                    rows={2}
                    value={finalizationNotes}
                  />
                </label>
                <label>
                  Cancellation reason
                  <textarea
                    onChange={(event) => setCancellationReason(event.target.value)}
                    rows={2}
                    value={cancellationReason}
                  />
                </label>
                <div className="meeting-actions">
                  <button
                    disabled={isBusy}
                    onClick={() =>
                      void runOperation(async () => {
                        const updated = await finalizeCommitteeMeeting(
                          authToken,
                          meeting.id,
                          { finalization_notes: finalizationNotes.trim() || null },
                        );
                        setMeeting(updated);
                      })
                    }
                    type="button"
                  >
                    Finalize
                  </button>
                  <button
                    disabled={isBusy}
                    onClick={() =>
                      void runOperation(async () => {
                        const updated = await cancelCommitteeMeeting(
                          authToken,
                          meeting.id,
                          { cancellation_reason: cancellationReason.trim() || null },
                        );
                        setMeeting(updated);
                      })
                    }
                    type="button"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            <article className="meeting-report-card">
              <div>
                <p className="eyebrow">Decision Record</p>
                <h3>Committee Meeting Minutes DOCX</h3>
                <p>
                  Generate Meeting Minutes for DRAFT or FINALIZED records without
                  changing risk workflow transitions.
                </p>
              </div>
              <div className="meeting-actions">
                <button disabled={isBusy} onClick={() => void handleGenerateReport()} type="button">
                  Generate Minutes DOCX
                </button>
                {generatedReport && (
                  <button disabled={isBusy} onClick={() => void handleDownloadReport()} type="button">
                    Download DOCX
                  </button>
                )}
              </div>
            </article>
          </section>
        </>
      )}
    </section>
  );
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function formatLabel(value: string | null | undefined): string {
  if (!value) {
    return "Not recorded";
  }
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
