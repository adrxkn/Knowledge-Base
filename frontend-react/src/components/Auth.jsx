import { useState } from "react";
import { loginUser, registerUser } from "../api";

export default function Auth({ onLogin }) {
  const [tab, setTab] = useState("login");
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [registerForm, setRegisterForm] = useState({ username: "", email: "", password: "" });
  const [authError, setAuthError] = useState("");
  const [registerMsg, setRegisterMsg] = useState({ text: "", success: false });

  async function handleLogin() {
    setAuthError("");
    const res = await loginUser(loginForm.username, loginForm.password);
    const data = await res.json();
    if (data.access_token) {
      onLogin(data.access_token);
    } else {
      setAuthError("Incorrect username or password");
    }
  }

  async function handleRegister() {
    setRegisterMsg({ text: "", success: false });
    const res = await registerUser(registerForm.username, registerForm.email, registerForm.password);
    if (res.ok) {
      setRegisterMsg({ text: "Account created! Sign in to continue.", success: true });
      setTimeout(() => setTab("login"), 1400);
    } else {
      const err = await res.json();
      setRegisterMsg({ text: err.detail || "Registration failed", success: false });
    }
  }

  function handleKey(e, fn) {
    if (e.key === "Enter") fn();
  }

  return (
    <div id="authPage">
      <div className="auth-card">
        <div className="auth-logo"><span className="dot"></span> Knowledge Base</div>
        <p className="auth-subtitle">Your AI-powered knowledge workspace</p>

        <div className="auth-tabs">
          <button className={`auth-tab${tab === "login" ? " active" : ""}`} onClick={() => setTab("login")}>Sign In</button>
          <button className={`auth-tab${tab === "register" ? " active" : ""}`} onClick={() => setTab("register")}>Create Account</button>
        </div>

        {tab === "login" && (
          <div className="auth-panel active">
            <div className="field">
              <label>Username</label>
              <input
                placeholder="your_username"
                autoComplete="username"
                value={loginForm.username}
                onChange={e => setLoginForm(p => ({ ...p, username: e.target.value }))}
                onKeyDown={e => handleKey(e, handleLogin)}
              />
            </div>
            <div className="field">
              <label>Password</label>
              <input
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                value={loginForm.password}
                onChange={e => setLoginForm(p => ({ ...p, password: e.target.value }))}
                onKeyDown={e => handleKey(e, handleLogin)}
              />
            </div>
            <button className="btn-primary" onClick={handleLogin}>Sign In</button>
            {authError && <p className="status-msg">{authError}</p>}
          </div>
        )}

        {tab === "register" && (
          <div className="auth-panel active">
            <div className="field">
              <label>Username</label>
              <input
                placeholder="your_username"
                autoComplete="username"
                value={registerForm.username}
                onChange={e => setRegisterForm(p => ({ ...p, username: e.target.value }))}
              />
            </div>
            <div className="field">
              <label>Email</label>
              <input
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
                value={registerForm.email}
                onChange={e => setRegisterForm(p => ({ ...p, email: e.target.value }))}
              />
            </div>
            <div className="field">
              <label>Password</label>
              <input
                type="password"
                placeholder="••••••••"
                autoComplete="new-password"
                value={registerForm.password}
                onChange={e => setRegisterForm(p => ({ ...p, password: e.target.value }))}
                onKeyDown={e => handleKey(e, handleRegister)}
              />
            </div>
            <button className="btn-primary" onClick={handleRegister}>Create Account</button>
            {registerMsg.text && (
              <p className={`status-msg${registerMsg.success ? " success" : ""}`}>{registerMsg.text}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}