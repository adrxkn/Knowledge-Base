  const API = "http://localhost:8000";

function authHeaders() {
  const token = localStorage.getItem("token");
  return { Authorization: `Bearer ${token}` };
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) }
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.reload();
    return null;
  }
  return res;
}

export const loginUser = (username, password) => {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  return fetch(`${API}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form
  });
};

export const registerUser = (username, email, password) =>
  fetch(`${API}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password })
  });

export const getWorkspaces = () => apiFetch(`${API}/workspaces`);
export const createWorkspace = (name) => apiFetch(`${API}/workspaces`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name })
});
export const joinWorkspace = (code) => apiFetch(`${API}/workspaces/join/${code}`, { method: "POST" });

export const getMembers = (wsId) => apiFetch(`${API}/workspaces/${wsId}/members`);
export const updateMemberRole = (wsId, userId, role) => apiFetch(`${API}/workspaces/${wsId}/members/${userId}`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ role })
});
export const removeMember = (wsId, userId) => apiFetch(`${API}/workspaces/${wsId}/members/${userId}`, { method: "DELETE" });
export const generateInvite = (wsId) => apiFetch(`${API}/workspaces/${wsId}/invite`, { method: "POST" });

export const getDocuments = (wsId) => apiFetch(`${API}/documents/${wsId}`);
export const uploadDocument = (wsId, file) => {
  const form = new FormData();
  form.append("file", file);
  return apiFetch(`${API}/upload/${wsId}`, { method: "POST", body: form });
};
export const deleteDocument = (docId) => apiFetch(`${API}/documents/${docId}`, { method: "DELETE" });
export const getDocumentStatus = (docId) => apiFetch(`${API}/document-status/${docId}`);

export const getChatHistory = (wsId) => apiFetch(`${API}/chat-history/${wsId}`);
export const streamAnswer = (wsId, question) =>
  fetch(`${API}/ask-stream/${wsId}?question=${encodeURIComponent(question)}`, {
    method: "POST",
    headers: authHeaders()
  });

export const getSettings = () => apiFetch(`${API}/settings`);
export const updateSettings = (settings) => apiFetch(`${API}/settings`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(settings)
});