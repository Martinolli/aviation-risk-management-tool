import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { getMyDecisionQueue } from "../api/decisionQueue";
import {
  downloadGeneratedReport,
  generateCommitteeMeetingPack,
  saveBlobAsFile,
} from "../api/reports";
import type {
  GeneratedReportRead,
  MyDecisionQueueRead,
  RiskRecordRead,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";

type MeetingPacksState =
  | { status: "loading" }
  | { status: "success"; queue: MyDecisionQueueRead }
  | { status: "error"; message: string };

export function CommitteeMeetingPacksPage() {
  const { isAuthenticated, token } = useAuth();
  const [pageState, setPageState] = useState<MeetingPacksState>({
    status: "loading",
  });
  const [selectedCommitteeId, setSelectedCommitteeId] = useState("");
  const [meetingTitle, setMeetingTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [generatedReport, setGeneratedReport] =
    useState<GeneratedReportRead | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    let isCurrent = true;
    if (!token) {
      return;
    }
    const tokenToUse = token;

    async function loadQueue() {
      try {
        const queue = await getMyDecisionQueue(tokenToUse);
        if (isCurrent) {
          setPageState({ status: "success", queue });
          setSelectedCommitteeId(
            (current) => current || queue.committees[0]?.committee_id || "",
          );
        }
      } catch (error) {
        if (isCurrent) {
          setPageState({
            status: "error",
            message:
              error instanceof ApiError
                ? error.message
                : "Please try again shortly.",
          });
        }
      }
    }

    void loadQueue();
    return () => {
      isCurrent = false;
    };
  }, [token]);

  if (!isAuthenticated || !token) {
    return <Navigate replace to="/login" />;
  }

  const queue = pageState.status === "success" ? pageState.queue : null;
  const selectedCommittee = queue?.committees.find(
    (committee) => committee.committee_id === selectedCommitteeId,
  );
  const queuePreview =
    queue?.queue_items.filter(
      (item) => item.committee_id === selectedCommitteeId,
    ) ?? [];

  async function handleGenerate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedCommitteeId || !token) {
      return;
    }

    setIsGenerating(true);
    setGenerationError(null);
    setDownloadError(null);
    try {
      const report = await generateCommitteeMeetingPack(
        token,
        selectedCommitteeId,
        {
          meeting_title: meetingTitle.trim() || null,
          meeting_date: meetingDate || null,
        },
      );
      setGeneratedReport(report);
    } catch (error) {
      setGenerationError(
        error instanceof ApiError
          ? error.message
          : "Unable to generate Committee Meeting Pack.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleDownload() {
    if (!generatedReport || !token) {
      return;
    }
    setIsDownloading(true);
    setDownloadError(null);
    try {
      const { blob, filename } = await downloadGeneratedReport(
        token,
        generatedReport.id,
      );
      saveBlobAsFile(blob, filename);
    } catch (error) {
      setDownloadError(
        error instanceof ApiError
          ? error.message
          : "Unable to download Committee Meeting Pack.",
      );
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <section
      className="meeting-packs-page"
      aria-labelledby="meeting-packs-heading"
    >
      <header className="page-header">
        <div>
          <p className="eyebrow">Committee preparation</p>
          <h1 id="meeting-packs-heading">Committee Meeting Packs</h1>
          <p>
            Generate agenda packs from the current decision queue for committees
            where you have authorized access.
          </p>
        </div>
      </header>

      {pageState.status === "loading" && (
        <p aria-live="polite" className="workspace-status" role="status">
          Loading committee Decision Queue...
        </p>
      )}
      {pageState.status === "error" && (
        <div className="workspace-alert" role="alert">
          <strong>Unable to load committee access.</strong>
          <span>{pageState.message}</span>
        </div>
      )}
      {queue && queue.committees.length === 0 && (
        <section className="meeting-pack-empty" aria-live="polite">
          <h2>No active committees</h2>
          <p>
            You are not an active member of a committee with an available
            Decision Queue.
          </p>
        </section>
      )}

      {queue && queue.committees.length > 0 && (
        <>
          <form className="meeting-pack-form" onSubmit={handleGenerate}>
            <label htmlFor="meeting-pack-committee">Committee</label>
            <select
              id="meeting-pack-committee"
              onChange={(event) => {
                setSelectedCommitteeId(event.target.value);
                setGeneratedReport(null);
              }}
              required
              value={selectedCommitteeId}
            >
              {queue.committees.map((committee) => (
                <option
                  key={committee.committee_id}
                  value={committee.committee_id}
                >
                  {committee.committee_name} - {committee.authority_level}
                </option>
              ))}
            </select>

            <label htmlFor="meeting-pack-title">Meeting Title (optional)</label>
            <input
              id="meeting-pack-title"
              maxLength={255}
              onChange={(event) => setMeetingTitle(event.target.value)}
              placeholder="Monthly committee review"
              type="text"
              value={meetingTitle}
            />

            <label htmlFor="meeting-pack-date">Meeting Date (optional)</label>
            <input
              id="meeting-pack-date"
              onChange={(event) => setMeetingDate(event.target.value)}
              type="date"
              value={meetingDate}
            />

            <div className="meeting-pack-actions">
              <button disabled={isGenerating} type="submit">
                {isGenerating ? "Generating..." : "Generate Meeting Pack"}
              </button>
            </div>
          </form>

          {generationError && (
            <p className="report-error" role="alert">
              {generationError}
            </p>
          )}

          {generatedReport && (
            <article className="meeting-pack-report-card" aria-live="polite">
              <div>
                <p className="eyebrow">Generated report</p>
                <h2>Committee Meeting Pack</h2>
                <dl>
                  <div>
                    <dt>Report type</dt>
                    <dd>Committee Meeting Pack</dd>
                  </div>
                  <div>
                    <dt>Generated at</dt>
                    <dd>{formatDateTime(generatedReport.generated_at)}</dd>
                  </div>
                  <div>
                    <dt>Committee</dt>
                    <dd>
                      {selectedCommittee?.committee_name ||
                        generatedReport.committee_id ||
                        "Not available"}
                    </dd>
                  </div>
                </dl>
              </div>
              <button
                disabled={isDownloading}
                onClick={() => void handleDownload()}
                type="button"
              >
                {isDownloading ? "Downloading..." : "Download DOCX"}
              </button>
            </article>
          )}

          {downloadError && (
            <p className="report-error" role="alert">
              {downloadError}
            </p>
          )}

          <section
            className="meeting-pack-preview"
            aria-labelledby="meeting-pack-preview-heading"
          >
            <div>
              <p className="eyebrow">Current queue</p>
              <h2 id="meeting-pack-preview-heading">Decision Queue preview</h2>
              <p>
                {selectedCommittee?.committee_name} - {queuePreview.length} risks
                awaiting committee decision
              </p>
            </div>

            {queuePreview.length === 0 ? (
              <p className="meeting-pack-empty">
                No risks are currently waiting for this committee decision.
              </p>
            ) : (
              <ul className="meeting-pack-risk-list">
                {queuePreview.map((item) => {
                  const risk = item.risk_record;
                  return (
                    <li key={risk.id}>
                      <div>
                        <Link to={`/risks/${risk.id}`}>
                          {getRiskDisplayId(risk)}
                        </Link>
                        <span>{formatLabel(risk.domain)}</span>
                        <span>{formatLabel(risk.workflow_status)}</span>
                      </div>
                      <p>{risk.problem_description}</p>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </>
      )}
    </section>
  );
}

function getRiskDisplayId(risk: RiskRecordRead): string {
  return risk.risk_id || risk.id.slice(0, 8);
}

function formatDateTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? "Not available"
    : parsed.toLocaleString();
}

function formatLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
