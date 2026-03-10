import { useState, useEffect } from "react";
import { getWorkspaces, createWorkspace, joinWorkspace } from "../api";

export default function Sidebar({ collapsed, onToggle, currentWorkspace, onSelectWorkspace, onLogout, onSettings }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [newName, setNewName] = useState("");
  const [joinCode, setJoinCode] = useState("");

  useEffect(() => { loadWorkspaces(); }, []);

  async function loadWorkspaces() {
    const res = await getWorkspaces();
    if (!res) return;
    const data = await res.json();
    setWorkspaces(data);
  }

  async function handleCreate() {
    const name = newName.trim();
    if (!name) return;
    const res = await createWorkspace(name);
    if (res && res.ok) {
      setNewName("");
      loadWorkspaces();
    }
  }

  async function handleJoin() {
    const code = joinCode.trim();
    if (!code) return;
    const res = await joinWorkspace(code);
    if (!res) return;
    const data = await res.json();
    setJoinCode("");
    if (res.ok) {
      alert(`Joined "${data.workspace_name}"! Your role is pending — wait for the owner to grant access.`);
      loadWorkspaces();
    } else {
      alert(data.detail || "Failed to join workspace");
    }
  }

  return (
    <>
      <button
        className={`sidebar-toggle${collapsed ? " collapsed" : ""}`}
        onClick={onToggle}
        style={{ left: collapsed ? 0 : 300 }}
      >
        {collapsed ? "›" : "‹"}
      </button>

      <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo"><span className="dot"></span> Knowledge Base</div>
          <div className="sidebar-tagline">AI Knowledge Workspace</div>
        </div>

        <div className="sidebar-section-label">Workspaces</div>

        <div className="workspace-list">
          {workspaces.map(w => (
            <div
              key={w.id}
              className={`workspace-item${currentWorkspace?.id === w.id ? " active" : ""}`}
              onClick={() => onSelectWorkspace(w)}
            >
              <span className="ws-icon">📁</span>
              <span className="workspace-item-name">{w.name}</span>
              <span className={`role-badge ${w.role}`}>{w.role}</span>
            </div>
          ))}
        </div>

        <div className="sidebar-create">
          <div className="create-row">
            <input
              className="sidebar-input"
              placeholder="Create new workspace"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleCreate()}
            />
            <button className="btn-create" onClick={handleCreate}>+</button>
          </div>
        </div>

        <div className="sidebar-join">
          <div className="join-row">
            <input
              className="sidebar-input"
              placeholder="Invite code"
              value={joinCode}
              onChange={e => setJoinCode(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleJoin()}
            />
            <button className="btn-join" onClick={handleJoin}>Join</button>
          </div>
        </div>

        <div className="sidebar-footer">
          <button className="btn-logout" onClick={onLogout}>↩ Sign out</button>
          <button className="btn-settings" onClick={onSettings} title="Settings">⚙</button>
        </div>
      </aside>
    </>
  );
}