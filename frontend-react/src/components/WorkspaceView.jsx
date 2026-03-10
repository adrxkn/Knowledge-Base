import { useState } from "react";
import DocumentPanel from "./DocumentPanel";
import ChatPanel from "./Chatpanel";
import MembersModal from "./MembersModal";

export default function WorkspaceView({ workspace, role }) {
  const [showMembers, setShowMembers] = useState(false);

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
      <div className="topbar">
        <div className="topbar-title">{workspace.name}</div>
        <div className="topbar-right">
          {role === "owner" && (
            <button className="btn-members" onClick={() => setShowMembers(true)}>
              👥 Members
            </button>
          )}
        </div>
      </div>

      <div className="content-area">
        <DocumentPanel workspaceId={workspace.id} role={role} />
        <ChatPanel workspaceId={workspace.id} />
      </div>

      {showMembers && (
        <MembersModal workspaceId={workspace.id} onClose={() => setShowMembers(false)} />
      )}
    </div>
  );
}