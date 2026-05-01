import React, { useEffect, useRef, useState } from "react";
import { fetchJson } from "../api.js";

function chatConnText(cfg) {
  if (!cfg || !Object.keys(cfg).length) return { className: "chat-conn warn", text: "" };
  if (cfg.chat_completions_configured) {
    let host = cfg.chat_completion_url ? String(cfg.chat_completion_url) : "";
    if (host.startsWith("https://")) host = host.slice(8);
    else if (host.startsWith("http://")) host = host.slice(7);
    return {
      className: "chat-conn ok",
      text:
        "Qwen chat: connected (" +
        (host || "endpoint") +
        ")" +
        (cfg.chat_model ? " · model " + cfg.chat_model : "") +
        ". Run agent (OpenAI) uses your OPENAI secret separately.",
    };
  }
  if (cfg.chat_completion_url) {
    return {
      className: "chat-conn warn",
      text:
        "Chat (Qwen): URL set — add CHAT_API_KEY or set CHAT_ALLOW_NO_AUTH=1. Chat does not use OpenAI keys.",
    };
  }
  return {
    className: "chat-conn warn",
    text:
      "Chat (Qwen): set CHAT_COMPLETIONS_URL (…/v1/chat/completions), CHAT_MODEL, and CHAT_API_KEY unless CHAT_ALLOW_NO_AUTH=1.",
  };
}

/** Left column — bottom: Qwen chat; patches flow up via onPatches. */
export function ChatPanel({ config, configFailed, onPatches }) {
  const [lines, setLines] = useState([]);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [sending, setSending] = useState(false);
  const logRef = useRef(null);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  const conn = configFailed
    ? {
        className: "chat-conn warn",
        text: "Chat: /api/config failed — cannot show connection status.",
      }
    : chatConnText(config);

  async function sendChat() {
    const msg = input.trim();
    if (!msg || sending) return;
    setInput("");
    setLines((prev) => [...prev, { role: "user", content: msg }]);
    setSending(true);
    try {
      const data = await fetchJson("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, history }),
      });
      const reply = data.reply || "";
      setLines((prev) => [...prev, { role: "assistant", content: reply }]);
      setHistory((h) => [...h, { role: "user", content: msg }, { role: "assistant", content: reply }]);
      onPatches(data.patches || []);
    } catch (e) {
      setLines((prev) => [...prev, { role: "assistant", content: "Error: " + (e.message || String(e)) }]);
      setHistory((h) => [...h, { role: "user", content: msg }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="panel chat-panel" aria-labelledby="lbl-chat">
      <div className="panel-head">
        <h2 id="lbl-chat">Chat</h2>
        <p>
          Conversational <strong>Qwen</strong> intake: it captures requirements into the matching inbox sections,
          fills what it can each turn, and asks follow-ups (e.g. date/time) when fields are missing. Uses{" "}
          <code>CHAT_*</code> only — not OpenAI.
        </p>
        <p className={conn.className}>{conn.text}</p>
      </div>
      <div className="panel-body" style={{ display: "flex", flexDirection: "column" }}>
        <div id="chat-log" ref={logRef} aria-live="polite">
          {lines.map((line, i) => (
            <div key={i} className={"chat-bubble " + line.role}>
              <div className="role">{line.role === "user" ? "You" : "Assistant"}</div>
              <span className="chat-bubble-text">{line.content}</span>
            </div>
          ))}
        </div>
        <div className="chat-input-row">
          <textarea
            id="chat-input"
            placeholder="Describe goals, audience, dates, assets…"
            rows={3}
            value={input}
            disabled={sending}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(ev) => {
              if (ev.key === "Enter" && !ev.shiftKey) {
                ev.preventDefault();
                sendChat();
              }
            }}
          />
          <button type="button" className="btn" disabled={sending} onClick={sendChat}>
            Send
          </button>
        </div>
      </div>
    </section>
  );
}
