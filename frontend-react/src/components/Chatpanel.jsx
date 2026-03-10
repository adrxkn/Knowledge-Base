import { useState, useEffect, useRef } from "react";
import { marked } from "marked";
import { getChatHistory, streamAnswer } from "../api";

marked.setOptions({ breaks: true, gfm: true });

const FOLLOWUP_CHIPS = [
  "Explain in more detail",
  "Give me an example",
  "Simplify this",
  "What are the key points?",
];

function Message({ role, text, sources, onChipClick }) {
  return (
    <div className={`message ${role}`}>
      <div className="msg-avatar">{role === "user" ? "You" : "AI"}</div>
      <div className="msg-body">
        <div className="msg-role">{role === "user" ? "You" : "Assistant"}</div>
        <div
          className="msg-bubble"
          dangerouslySetInnerHTML={{ __html: marked.parse(text) }}
        />
        {sources && sources.length > 0 && (
          <div className="msg-sources">
            {[...new Map(sources.map(s => [s.document, s])).values()].map(s => (
              <span key={s.document} className="source-chip" title={s.document}>
                📄 {s.document}
              </span>
            ))}
          </div>
        )}
        {role === "ai" && onChipClick && (
          <div className="followup-chips">
            {FOLLOWUP_CHIPS.map(chip => (
              <button key={chip} className="followup-chip" onClick={() => onChipClick(chip)}>
                {chip}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPanel({ workspaceId }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamSources, setStreamSources] = useState(null);
  const chatRef = useRef();
  const textareaRef = useRef();

  useEffect(() => {
    loadHistory();
  }, [workspaceId]);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages, streamText]);

  async function loadHistory() {
    setMessages([]);
    const res = await getChatHistory(workspaceId);
    if (!res || !res.ok) return;
    const data = await res.json();
    const loaded = [];
    data.forEach(m => {
      loaded.push({ role: "user", text: m.question });
      loaded.push({ role: "ai", text: m.answer });
    });
    setMessages(loaded);
  }

  async function handleAsk(q) {
    const text = (q || question).trim();
    if (!text || streaming) return;
    setQuestion("");
    autoResize(textareaRef.current);

    setMessages(prev => [...prev, { role: "user", text }]);
    setStreaming(true);
    setStreamText("");
    setStreamSources(null);

    try {
      const res = await streamAnswer(workspaceId, text);
      if (res.status === 401) { window.location.reload(); return; }
      if (!res.ok) throw new Error("Request failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.trim()) continue;
          const prefix = line[0];
          const payload = line.slice(2);

          if (prefix === "0") {
            const token = JSON.parse(payload);
            full += token;
            setStreamText(full);
          } else if (prefix === "1") {
            const sources = JSON.parse(payload);
            setStreamSources(sources);
          }
        }
      }

      setMessages(prev => [...prev, { role: "ai", text: full, sources: streamSources }]);
    } catch {
      setMessages(prev => [...prev, { role: "ai", text: "Could not reach the AI model." }]);
    } finally {
      setStreaming(false);
      setStreamText("");
      setStreamSources(null);
    }
  }

  function autoResize(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }

  const hasMessages = messages.length > 0 || streaming;

  return (
    <div className="chat-panel">
      <div className="chat-messages" ref={chatRef}>
        {!hasMessages && (
          <div className="chat-welcome">
            <h3>Ask anything</h3>
            <p>Upload documents to this workspace, then ask questions and get AI-powered answers from your content.</p>
          </div>
        )}

        {messages.map((m, i) => (
          <Message
            key={i}
            role={m.role}
            text={m.text}
            sources={m.sources}
            onChipClick={m.role === "ai" && i === messages.length - 1 ? handleAsk : null}
          />
        ))}

        {streaming && (
          <div className="message ai">
            <div className="msg-avatar">AI</div>
            <div className="msg-body">
              <div className="msg-role">Assistant</div>
              <div className="msg-bubble">
                {streamText
                  ? <span dangerouslySetInnerHTML={{ __html: marked.parse(streamText) + '<span class="streaming-cursor"></span>' }} />
                  : <div className="thinking"><span /><span /><span /></div>
                }
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="chat-input-area">
        <div className="chat-input-wrap">
          <textarea
            ref={textareaRef}
            className="question-input"
            placeholder="Ask a question about your documents…"
            rows={1}
            value={question}
            onChange={e => { setQuestion(e.target.value); autoResize(e.target); }}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
            disabled={streaming}
          />
          <button className="btn-ask" onClick={() => handleAsk()} disabled={streaming}>➤</button>
        </div>
        <div className="chat-hint">Enter to send · Shift+Enter for new line</div>
      </div>
    </div>
  );
}