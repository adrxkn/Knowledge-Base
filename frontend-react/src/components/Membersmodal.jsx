import { useState, useEffect } from "react";
import { getMembers, updateMemberRole, removeMember, generateInvite } from "../api";

export default function MembersModal({ workspaceId, onClose }) {
  const [members, setMembers] = useState([]);
  const [inviteCode, setInviteCode] = useState(null);
  const [inviteExpiry, setInviteExpiry] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => { loadMembers(); }, [workspaceId]);

  async function loadMembers() {
    const res = await getMembers(workspaceId);
    if (!res || !res.ok) return;
    setMembers(await res.json());
  }

  async function handleRoleChange(userId, role) {
    const res = await updateMemberRole(workspaceId, userId, role);
    if (!res) return;
    if (!res.ok) {
      const d = await res.json();
      alert(d.detail || "Failed to update role");
      loadMembers();
    }
  }

  async function handleRemove(userId) {
    if (!confirm("Remove this member from the workspace?")) return;
    const res = await removeMember(workspaceId, userId);
    if (res && res.ok) loadMembers();
    else { const d = await res.json(); alert(d.detail || "Failed to remove member"); }
  }

  async function handleGenerateInvite() {
    const res = await generateInvite(workspaceId);
    if (!res) return;
    const data = await res.json();
    if (!res.ok) { alert(data.detail || "Failed to generate invite"); return; }
    setInviteCode(data.code);
    setInviteExpiry(data.expires_at);
  }

  function handleCopy() {
    navigator.clipboard.writeText(inviteCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="modal-overlay active" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">Members</div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="modal-section-label">Members</div>
          {members.map(m => (
            <div key={m.user_id} className="member-item">
              <div className="member-avatar">{m.username[0].toUpperCase()}</div>
              <div className="member-name">{m.username}</div>
              <select
                className="member-role-select"
                value={m.role}
                onChange={e => handleRoleChange(m.user_id, e.target.value)}
              >
                <option value="pending">Pending</option>
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
                <option value="owner">Owner</option>
              </select>
              <button className="btn-remove" onClick={() => handleRemove(m.user_id)}>Remove</button>
            </div>
          ))}

          <div className="modal-section-label">Invite Link</div>
          {inviteCode ? (
            <>
              <div className="invite-box">
                <div className="invite-code">{inviteCode}</div>
                <button className="btn-copy" onClick={handleCopy}>
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
              <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 8 }}>
                Expires in 7 days · Anyone with this code joins as Pending
              </div>
              <button className="btn-generate" onClick={handleGenerateInvite}>+ Generate new link</button>
            </>
          ) : (
            <button className="btn-generate" onClick={handleGenerateInvite}>+ Generate invite link</button>
          )}
        </div>
      </div>
    </div>
  );
}