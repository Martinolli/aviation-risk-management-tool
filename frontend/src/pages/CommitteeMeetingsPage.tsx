import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  createCommitteeMeeting,
  listCommitteeMeetings,
} from "../api/committeeMeetings";
import { getMyDecisionQueue } from "../api/decisionQueue";
import type {
  CommitteeMeetingRead,
  CommitteeMeetingStatus,
  MyDecisionQueueRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type MeetingsState =
  | { status: "loading" }
  | { status: "success"; meetings: CommitteeMeetingRead[] }
  | { status: "error"; message: string };

export function CommitteeMeetingsPage() {
  const { isAuthenticated, token } = useAuth();
  const navigate = useNavigate();
  const [meetingsState, setMeetingsState] = useState<MeetingsState>({
    status: "loading",
  });
  const [queue, setQueue] = useState<MyDecisionQueueRead | null>(null);
  const [committeeFilter, setCommitteeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<CommitteeMeetingStatus | "">("");
  const [form, setForm] = useState({
    committee_id: "",
    title: "",
    meeting_date: "",
    location: "",
    chair_user_id: "",
    agenda_summary: "",
    discussion_summary: "",
    decisions_summary: "",
    action_items_summary: "",
  });
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    let isCurrent = true;
    if (!token) {
      return;
    }
    const tokenToUse = token;

    async function load() {
      setMeetingsState({ status: "loading" });
      try {
        const [meetingRows, queueData] = await Promise.all([
          listCommitteeMeetings(tokenToUse, {
            committeeId: committeeFilter || undefined,
            status: statusFilter || undefined,
          }),
          getMyDecisionQueue(tokenToUse),
        ]);
        if (!isCurrent) {
          return;
        }
        setMeetingsState({ status: "success", meetings: meetingRows });
        setQueue(queueData);
        setForm((current) => ({
          ...current,
          committee_id:
            current.committee_id || queueData.committees[0]?.committee_id || "",
        }));
      } catch (error) {
        if (isCurrent) {
          setMeetingsState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Unable to load Meeting Minutes.",
          });
        }
      }
    }

    void load();
    return () => {
      isCurrent = false;
    };
  }, [token, committeeFilter, statusFilter]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }
    setIsCreating(true);
    setCreateError(null);
    try {
      const meeting = await createCommitteeMeeting(token, {
        committee_id: form.committee_id,
        title: form.title.trim(),
        meeting_date: form.meeting_date,
        location: form.location.trim() || null,
        chair_user_id: form.chair_user_id.trim() || null,
        agenda_summary: form.agenda_summary.trim() || null,
        discussion_summary: form.discussion_summary.trim() || null,
        decisions_summary: form.decisions_summary.trim() || null,
        action_items_summary: form.action_items_summary.trim() || null,
      });
      navigate(`/committee-meetings/${meeting.id}`);
    } catch (error) {
      setCreateError(
        error instanceof ApiError
          ? error.message
          : "Unable to create Committee Meeting Minutes.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  const committees = queue?.committees ?? [];

  return (
    <section className="committee-meetings-page" aria-labelledby="meetings-heading">
      <header className="page-header">
        <div>
          <p className="eyebrow">Meeting Minutes</p>
          <h1 id="meetings-heading">Committee Meeting Minutes</h1>
          <p>
            Capture Attendance, Agenda Item notes, Decision Record links, and
            Action Items for committees where you are an active member.
          </p>
        </div>
      </header>

      <section className="meeting-section" aria-labelledby="create-meeting-heading">
        <h2 id="create-meeting-heading">Create Meeting</h2>
        {createError && (
          <p className="meeting-warning" role="alert">
            {createError}
          </p>
        )}
        <form className="meeting-form-grid" onSubmit={handleCreate}>
          <label>
            Committee
            <select
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  committee_id: event.target.value,
                }))
              }
              required
              value={form.committee_id}
            >
              <option value="">Select committee</option>
              {committees.map((committee) => (
                <option
                  key={committee.committee_id}
                  value={committee.committee_id}
                >
                  {committee.committee_name} - {committee.authority_level}
                </option>
              ))}
            </select>
          </label>
          <label>
            Title
            <input
              maxLength={255}
              onChange={(event) =>
                setForm((current) => ({ ...current, title: event.target.value }))
              }
              required
              value={form.title}
            />
          </label>
          <label>
            Meeting date
            <input
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  meeting_date: event.target.value,
                }))
              }
              required
              type="date"
              value={form.meeting_date}
            />
          </label>
          <label>
            Location
            <input
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  location: event.target.value,
                }))
              }
              value={form.location}
            />
          </label>
          <label>
            Chair user ID
            <input
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  chair_user_id: event.target.value,
                }))
              }
              value={form.chair_user_id}
            />
          </label>
          <label>
            Agenda summary
            <textarea
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  agenda_summary: event.target.value,
                }))
              }
              rows={3}
              value={form.agenda_summary}
            />
          </label>
          <label>
            General discussion
            <textarea
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  discussion_summary: event.target.value,
                }))
              }
              rows={3}
              value={form.discussion_summary}
            />
          </label>
          <label>
            Decisions summary
            <textarea
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  decisions_summary: event.target.value,
                }))
              }
              rows={3}
              value={form.decisions_summary}
            />
          </label>
          <label>
            Action items summary
            <textarea
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  action_items_summary: event.target.value,
                }))
              }
              rows={3}
              value={form.action_items_summary}
            />
          </label>
          <div className="meeting-actions">
            <button disabled={isCreating} type="submit">
              {isCreating ? "Creating..." : "Create Meeting"}
            </button>
          </div>
        </form>
      </section>

      <section className="meeting-section" aria-labelledby="meeting-list-heading">
        <div className="meeting-section-header">
          <div>
            <h2 id="meeting-list-heading">Meetings</h2>
            <p>Visible meetings follow your active committee memberships.</p>
          </div>
          <div className="meeting-filters">
            <select
              aria-label="Filter by committee"
              onChange={(event) => setCommitteeFilter(event.target.value)}
              value={committeeFilter}
            >
              <option value="">All committees</option>
              {committees.map((committee) => (
                <option
                  key={committee.committee_id}
                  value={committee.committee_id}
                >
                  {committee.committee_name}
                </option>
              ))}
            </select>
            <select
              aria-label="Filter by status"
              onChange={(event) =>
                setStatusFilter(event.target.value as CommitteeMeetingStatus | "")
              }
              value={statusFilter}
            >
              <option value="">All statuses</option>
              <option value="DRAFT">DRAFT</option>
              <option value="FINALIZED">FINALIZED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>
        </div>

        {meetingsState.status === "loading" && (
          <p className="workspace-status" role="status">
            Loading Meeting Minutes...
          </p>
        )}
        {meetingsState.status === "error" && (
          <p className="meeting-warning" role="alert">
            {meetingsState.message}
          </p>
        )}
        {meetingsState.status === "success" &&
          meetingsState.meetings.length === 0 && (
            <p className="workspace-empty">No Meeting Minutes found.</p>
          )}
        {meetingsState.status === "success" &&
          meetingsState.meetings.length > 0 && (
            <ul className="committee-meeting-list">
              {meetingsState.meetings.map((meeting) => (
                <li className="committee-meeting-card" key={meeting.id}>
                  <div>
                    <h3>{meeting.title}</h3>
                    <div className="report-meta">
                      <span>{meeting.committee_name || meeting.committee_id}</span>
                      <span>Authority Level: {formatLabel(meeting.authority_level)}</span>
                      <span>{formatDate(meeting.meeting_date)}</span>
                      <span>{meeting.attendees.length} Attendance</span>
                      <span>{meeting.risk_items.length} Agenda Item</span>
                    </div>
                  </div>
                  <div className="meeting-actions">
                    <span className={`meeting-status-badge ${meeting.status.toLowerCase()}`}>
                      {meeting.status}
                    </span>
                    <Link className="button-link" to={`/committee-meetings/${meeting.id}`}>
                      Open
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
      </section>
    </section>
  );
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString();
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
