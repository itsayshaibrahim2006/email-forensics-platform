import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api.js";

export default function Upload() {
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  function addFiles(fileList) {
    const emlFiles = Array.from(fileList).filter((f) => f.name.endsWith(".eml"));
    setFiles((prev) => [...prev, ...emlFiles]);
  }

  async function handleUpload() {
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const res = await api.uploadEmails(files);
      setResult(res);
      setFiles([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <h1>Upload Emails for Analysis</h1>
      <p className="subtitle">
        Upload raw .eml files. Each one is parsed, linked into a thread, geolocated hop-by-hop,
        checked for spoofing, and scored for risk.
      </p>

      <div className="panel">
        <div
          className={`dropzone ${dragOver ? "dragover" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            addFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          style={{ cursor: "pointer" }}
        >
          Drag & drop .eml files here, or click to browse
          <input
            ref={inputRef}
            type="file"
            accept=".eml"
            multiple
            hidden
            onChange={(e) => addFiles(e.target.files)}
          />
        </div>

        {files.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div className="subtitle" style={{ marginBottom: 8 }}>
              {files.length} file(s) ready:
            </div>
            <ul style={{ color: "var(--text-dim)", fontSize: 13 }}>
              {files.map((f, i) => <li key={i}>{f.name}</li>)}
            </ul>
            <button className="btn" disabled={uploading} onClick={handleUpload}>
              {uploading ? "Analyzing…" : `Analyze ${files.length} email(s)`}
            </button>
          </div>
        )}

        {error && <div className="error-state">{error}</div>}

        {result && (
          <div style={{ marginTop: 20 }}>
            <div className="badge low">DONE</div>
            <p style={{ marginTop: 10 }}>
              Parsed {result.uploaded} email(s) into {result.thread_ids.length} thread(s).
            </p>
            <button className="btn secondary" onClick={() => navigate("/threads")}>
              View Threads →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
