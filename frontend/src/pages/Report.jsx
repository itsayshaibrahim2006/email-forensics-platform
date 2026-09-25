import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api.js";

export default function Report() {
  const { emailId } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(true);

  useEffect(() => {
    setGenerating(true);
    api.generateReport(emailId)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setGenerating(false));
  }, [emailId]);

  if (error) return <div className="error-state">{error}</div>;
  if (generating || !report) return <div className="empty-state">Compiling forensic report…</div>;

  return (
    <div>
      <Link to={-1} style={{ color: "var(--text-dim)", fontSize: 13 }}>← Back</Link>
      <h1 style={{ marginTop: 10 }}>Forensic Report</h1>
      <p className="subtitle">Generated {new Date(report.generated_at).toLocaleString()}</p>

      <div className="panel">
        <h2>AI Investigator Narrative</h2>
        <p style={{ fontSize: 14 }}>{report.findings?.ai_risk_narrative}</p>
        <div style={{ marginTop: 10 }}>
          <span className={`badge ${report.risk_score >= 40 ? "high" : report.risk_score >= 15 ? "med" : "low"}`}>
            RISK SCORE {report.risk_score}/100
          </span>
        </div>
      </div>

      <div className="panel">
        <h2>Rule-Based Summary</h2>
        <p style={{ fontSize: 13, color: "var(--text-dim)" }}>{report.summary}</p>
      </div>

      <div className="panel">
        <h2>Chain of Custody</h2>
        <p style={{ fontSize: 13, color: "var(--text-dim)" }}>
          This report's findings are hashed below. Any modification to the findings after
          generation will change this hash, so investigators can verify evidence integrity.
        </p>
        <div className="hash">{report.evidence_hash}</div>
      </div>

      <div className="panel">
        <h2>Export</h2>
        <p style={{ fontSize: 13, color: "var(--text-dim)" }}>
          Download this report for evidence filing or SIEM ingestion.
        </p>
        <div className="download-row">
          <a className="btn" href={api.downloadUrl(report.id, "pdf")}>Download PDF</a>
          <a className="btn secondary" href={api.downloadUrl(report.id, "json")}>Download JSON</a>
          <a className="btn secondary" href={api.downloadUrl(report.id, "csv")}>Download CSV</a>
        </div>
      </div>
    </div>
  );
}
