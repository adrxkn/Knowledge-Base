import { useState, useEffect } from "react";
import { getSettings, updateSettings } from "../api";

const DEFAULTS = {
  ollama_url: "http://localhost:11434",
  model_name: "llama3.2",
  chunk_size: "1000",
  chunk_overlap: "150",
  retrieval_top_k: "5",
};

export default function SettingsPage({ onBack }) {
  const [form, setForm] = useState(DEFAULTS);
  const [saveStatus, setSaveStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadSettings(); }, []);

  async function loadSettings() {
    const res = await getSettings();
    if (!res || !res.ok) { setLoading(false); return; }
    const data = await res.json();
    setForm(prev => ({ ...prev, ...data }));
    setLoading(false);
  }

  async function handleSave() {
    setSaveStatus("");
    const res = await updateSettings(form);
    if (!res) return;
    if (res.ok) {
      setSaveStatus("Saved!");
      setTimeout(() => setSaveStatus(""), 2500);
    } else {
      const d = await res.json();
      setSaveStatus(d.detail || "Failed to save");
    }
  }

  function set(key, val) { setForm(prev => ({ ...prev, [key]: val })); }

  if (loading) return (
    <div className="settings-page">
      <div className="settings-topbar">
        <button className="btn-back" onClick={onBack}>← Back</button>
        <div className="settings-title">Settings</div>
      </div>
      <div className="settings-body" style={{ color: "var(--muted)" }}>Loading…</div>
    </div>
  );

  return (
    <div className="settings-page">
      <div className="settings-topbar">
        <button className="btn-back" onClick={onBack}>← Back</button>
        <div className="settings-title">Settings</div>
      </div>

      <div className="settings-body">

        <div className="settings-section">
          <div className="settings-section-title">LLM Configuration</div>

          <div className="settings-field">
            <label>Ollama URL</label>
            <div className="field-hint">The endpoint where Ollama is running</div>
            <input
              value={form.ollama_url}
              onChange={e => set("ollama_url", e.target.value)}
              placeholder="http://localhost:11434"
            />
          </div>

          <div className="settings-field">
            <label>Model Name</label>
            <div className="field-hint">The Ollama model to use for answers (e.g. llama3.2, mistral)</div>
            <input
              value={form.model_name}
              onChange={e => set("model_name", e.target.value)}
              placeholder="llama3.2"
            />
          </div>
        </div>

        <div className="settings-section">
          <div className="settings-section-title">Retrieval Configuration</div>

          <div className="settings-field">
            <label>Chunk Size</label>
            <div className="field-hint">Number of characters per document chunk. Larger = more context, fewer chunks</div>
            <input
              type="number"
              value={form.chunk_size}
              onChange={e => set("chunk_size", e.target.value)}
              min={200}
              max={4000}
            />
          </div>

          <div className="settings-field">
            <label>Chunk Overlap</label>
            <div className="field-hint">Characters of overlap between consecutive chunks to avoid cutting context</div>
            <input
              type="number"
              value={form.chunk_overlap}
              onChange={e => set("chunk_overlap", e.target.value)}
              min={0}
              max={500}
            />
          </div>

          <div className="settings-field">
            <label>Retrieved Chunks (Top-K)</label>
            <div className="field-hint">Number of chunks sent to the LLM after reranking. Higher = more context but slower</div>
            <input
              type="number"
              value={form.retrieval_top_k}
              onChange={e => set("retrieval_top_k", e.target.value)}
              min={1}
              max={20}
            />
          </div>
        </div>

        <div className="settings-save">
          <button className="btn-save" onClick={handleSave}>Save Settings</button>
          {saveStatus && (
            <span className="save-status" style={{ color: saveStatus === "Saved!" ? "#2d7a4f" : "var(--accent)" }}>
              {saveStatus}
            </span>
          )}
        </div>

      </div>
    </div>
  );
}