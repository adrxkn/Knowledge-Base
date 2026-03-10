import { useState, useEffect } from "react";
import Auth from "./components/Auth";
import Sidebar from "./components/Sidebar";
import WorkspaceView from "./components/WorkspaceView";
import SettingsPage from "./components/SettingsPage";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [currentWorkspace, setCurrentWorkspace] = useState(null);
  const [currentRole, setCurrentRole] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [page, setPage] = useState("app"); 

  const handleLogin = (t) => {
    localStorage.setItem("token", t);
    setToken(t);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setCurrentWorkspace(null);
    setCurrentRole(null);
  };

  const openWorkspace = (ws) => {
    setCurrentWorkspace(ws);
    setCurrentRole(ws.role);
    setPage("app");
  };

  if (!token) return <Auth onLogin={handleLogin} />;

  if (page === "settings") return <SettingsPage onBack={() => setPage("app")} />;

  return (
    <div style={{ display: "flex", width: "100%", height: "100vh", overflow: "hidden" }}>
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(p => !p)}
        currentWorkspace={currentWorkspace}
        onSelectWorkspace={openWorkspace}
        onLogout={handleLogout}
        onSettings={() => setPage("settings")}
      />
      <main style={{ flex: 1, display: "flex", flexDirection: "column", background: "var(--paper)", overflow: "hidden" }}>
        {currentWorkspace
          ? <WorkspaceView
              workspace={currentWorkspace}
              role={currentRole}
            />
          : <EmptyState />
        }
      </main>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state" style={{ display: "flex" }}>
      <div className="empty-state-icon">📂</div>
      <h3>Select a workspace</h3>
      <p>Choose a workspace from the sidebar, or create a new one to get started.</p>
    </div>
  );
}