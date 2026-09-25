import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../api.js";

function riskBadgeClass(score) {
  if (score >= 40) return "high";
  if (score >= 15) return "med";
  return "low";
}

function ThreadList() {
  const [threads, setThreads] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.listThreads().then(setThreads).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error-state">{error}</div>;
  if (!threads) return <div className="empty-state">Loading threads…</div>;
  if (threads.length === 0) {
    return (
      <div className="empty-state">
        No threads yet. <Link to="/" style={{ color: "var(--cyan)" }}>Upload some emails</Link> to get started.
      </div>
    );
  }

  return (
    <div className="thread-list">
      {threads.map((t) => (
        <Link key={t.id} to={`/threads/${t.id}`} className="thread-row">
          <div>
            <div className="thread-subject">{t.subject_normalized || "(no subject)"}</div>
            <div className="thread-meta">{t.email_count} email(s)</div>
          </div>
          <span className={`badge ${riskBadgeClass(t.max_risk_score)}`}>
            RISK {t.max_risk_score}
          </span>
        </Link>
      ))}
    </div>
  );
}

function ThreadDetail({ threadId }) {
  const [thread, setThread] = useState(null);
  const [error, setError] = useState(null);
  const [summarizing, setSummarizing] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.getThread(threadId).then(setThread).catch((e) => setError(e.message));
  }, [threadId]);

  async function handleSummarize() {
    setSummarizing(true);
    try {
      const res = await api.summarizeThread(threadId);
      setThread((prev) => ({ ...prev, ai_summary: res.ai_summary }));
    } catch (e) {
      setError(e.message);
    } finally {
      setSummarizing(false);
    }
  }

  if (error) return <div className="error-state">{error}</div>;
  if (!thread) return <div className="empty-state">Loading thread…</div>;

  return (
    <div>
      <Link to="/threads" style={{ color: "var(--text-dim)", fontSize: 13 }}>← All threads</Link>
      <h1 style={{ marginTop: 10 }}>{thread.subject_normalized || "(no subject)"}</h1>
      <p className="subtitle">{thread.emails.length} email(s) in this thread, ordered by upload time</p>

      <div className="panel">
        <h2>AI Thread Summary</h2>
        {thread.ai_summary ? (
          <p style={{ fontSize: 14, color: "var(--text-dim)" }}>{thread.ai_summary}</p>
        ) : (
          <>
            <p style={{ fontSize: 13, color: "var(--text-dim)", marginBottom: 12 }}>
              Ask Claude to summarize this conversation and flag which message(s) look suspicious.
            </p>
            <button className="btn" disabled={summarizing} onClick={handleSummarize}>
              {summarizing ? "Summarizing…" : "Generate AI Summary"}
            </button>
          </>
        )}
      </div>

      {thread.emails.map((email) => (
        <div key={email.id} className="email-card">
          <div className="email-card-head">
            <div>
              <div className="email-from">{email.sender || "Unknown sender"}</div>
              <div className="email-subject">{email.subject}</div>
            </div>
            <span className={`badge ${riskBadgeClass(email.risk_score)}`}>
              RISK {email.risk_score}
            </span>
          </div>

          <div className="chip-row">
            <span className={`chip ${email.spf_result === "pass" ? "pass" : "fail"}`}>
              SPF: {email.spf_result || "none"}
            </span>
            <span className={`chip ${email.dkim_result === "pass" ? "pass" : "fail"}`}>
              DKIM: {email.dkim_result || "none"}
            </span>
            <span className={`chip ${email.dmarc_result === "pass" ? "pass" : "fail"}`}>
              DMARC: {email.dmarc_result || "none"}
            </span>
            {email.is_spoof_suspected && <span className="chip fail">SPOOFING SUSPECTED</span>}
          </div>

          {email.risk_summary && (
            <p style={{ fontSize: 13, color: "var(--text-dim)", marginTop: 10 }}>
              {email.risk_summary}
            </p>
          )}

          <div className="email-actions">
            <button className="btn small secondary" onClick={() => navigate(`/emails/${email.id}/map`)}>
              View Hop Map
            </button>
            <button className="btn small" onClick={() => navigate(`/emails/${email.id}/report`)}>
              Generate Report
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ThreadView() {
  const { threadId } = useParams();
  return (
    <div>
      {!threadId && (
        <>
          <h1>Investigation Threads</h1>
          <p className="subtitle">Reconstructed conversations, sorted by highest risk first.</p>
        </>
      )}
      {threadId ? <ThreadDetail threadId={threadId} /> : <ThreadList />}
    </div>
  );
}
