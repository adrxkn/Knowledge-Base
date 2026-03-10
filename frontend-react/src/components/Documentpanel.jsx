import { useState, useEffect, useRef } from "react";
import { getDocuments, uploadDocument, deleteDocument, getDocumentStatus } from "../api";

function docStatusBadge(status) {
  const map = {
    pending:    { label: "Queued",     color: "#b0a89e" },
    processing: { label: "Processing", color: "#c9501e" },
    ready:      { label: "",           color: "" },
    failed:     { label: "Failed",     color: "#dc2626" },
  };
  const s = map[status] || map.ready;
  if (!s.label) return null;
  return <span style={{ fontSize: 11, color: s.color, fontWeight: 500 }}>{s.label}</span>;
}

export default function DocumentPanel({ workspaceId, role }) {
  const [docs, setDocs] = useState([]);
  const [uploadState, setUploadState] = useState(null); 
  const [uploadMsg, setUploadMsg] = useState("");
  const fileInputRef = useRef();
  const canUpload = role === "owner" || role === "editor";
  const canDelete = role === "owner" || role === "editor";

  useEffect(() => { loadDocs(); }, [workspaceId]);

  async function loadDocs() {
    const res = await getDocuments(workspaceId);
    if (!res || !res.ok) return;
    setDocs(await res.json());
  }

  async function handleUpload(file) {
    if (!file) return;
    setUploadState("uploading");
    setUploadMsg("Uploading…");

    const res = await uploadDocument(workspaceId, file);
    fileInputRef.current.value = "";

    if (!res) return;
    if (res.ok) {
      const data = await res.json();
      setUploadState("success");
      setUploadMsg("Document uploaded ✓");
      loadDocs();
      pollStatus(data.id);
      setTimeout(() => setUploadState(null), 2500);
    } else if (res.status === 409) {
      const data = await res.json();
      setUploadState("error");
      setUploadMsg(data.detail);
      setTimeout(() => setUploadState(null), 3000);
    } else {
      setUploadState("error");
      setUploadMsg("Upload failed");
      setTimeout(() => setUploadState(null), 3000);
    }
  }

  function pollStatus(docId) {
    const interval = setInterval(async () => {
      try {
        const res = await getDocumentStatus(docId);
        if (!res || !res.ok) { clearInterval(interval); return; }
        const data = await res.json();
        loadDocs();
        if (data.status === "ready" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch { clearInterval(interval); }
    }, 2000);
  }

  async function handleDelete(docId) {
    if (!confirm("Delete this document? This cannot be undone.")) return;
    const res = await deleteDocument(docId);
    if (res && res.ok) loadDocs();
    else { const d = await res.json(); alert(d.detail || "Failed to delete"); }
  }

  return (
    <div className="docs-panel">
      <div className="panel-header">
        <span className="panel-title">Documents</span>
        <span className="doc-count">{docs.length}</span>
      </div>

      {uploadState && (
        <div style={{ padding: "8px 16px", borderBottom: "1px solid var(--border)" }}>
          <div className={`upload-progress${uploadState === "success" ? " success" : uploadState === "error" ? " error" : ""}`}>
            {uploadState === "uploading" && <div className="spinner" />}
            <span className="upload-msg">{uploadMsg}</span>
          </div>
        </div>
      )}

      {canUpload && (
        <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)" }}>
          <label
            className="upload-label"
            style={{ justifyContent: "center", fontSize: 13 }}
            onClick={() => fileInputRef.current.click()}
          >
            ↑ Upload Document
          </label>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            style={{ display: "none" }}
            onChange={e => handleUpload(e.target.files[0])}
          />
        </div>
      )}

      <div className="docs-list">
        {docs.length === 0 ? (
          <div className="docs-empty">No documents yet.<br />Upload a file to begin.</div>
        ) : docs.map(doc => {
          const ext = doc.filename.split(".").pop().toLowerCase();
          const icon = ext === "pdf" ? "📄" : ext === "md" ? "📝" : "📃";
          const kb = doc.file_size ? (doc.file_size / 1024).toFixed(1) + " KB" : "";
          const badge = docStatusBadge(doc.status);
          return (
            <div key={doc.id} className="doc-item">
              <div className="doc-icon">{icon}</div>
              <div className="doc-info">
                <div className="doc-name" title={doc.filename}>{doc.filename}</div>
                <div className="doc-meta">
                  {kb}{kb && badge ? " · " : ""}{badge}
                </div>
              </div>
              {canDelete && (
                <button className="btn-remove" onClick={() => handleDelete(doc.id)} title="Delete">✕</button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}