import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { notifyParentOfHeight } from "./postMessage.js";
import { fetchWidgetConfig } from "./useWidgetConfig.js";
import "./style.css";

function queryParam(name, fallback) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || fallback;
}

function App() {
  const apiBase = useMemo(() => queryParam("apiBase", "http://localhost:8000"), []);
  const widgetId = useMemo(() => queryParam("widgetId", "maintainers-copilot"), []);
  const hostOrigin = useMemo(() => queryParam("hostOrigin", window.location.origin), []);
  const [config, setConfig] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    fetchWidgetConfig({ apiBase, widgetId, hostOrigin })
      .then(setConfig)
      .catch((exc) => setError(exc.message));
  }, [apiBase, widgetId, hostOrigin]);

  useEffect(() => {
    if (rootRef.current) notifyParentOfHeight(rootRef.current.scrollHeight + 24);
  }, [config, messages, error, isSending]);

  async function sendMessage(event) {
    event.preventDefault();
    const content = input.trim();
    if (!content || isSending) return;

    const nextMessages = [...messages, { role: "user", content }];
    setMessages(nextMessages);
    setInput("");
    setIsSending(true);
    setError("");

    try {
      const response = await fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          messages: nextMessages,
          use_rag: true,
          top_k: 5,
          allow_summarizer: false,
          allow_memory_write: false,
          tools: ["auto"],
        }),
      });
      if (!response.ok) throw new Error(`Chat failed with HTTP ${response.status}`);
      const data = await response.json();
      setConversationId(data.conversation_id);
      setMessages([...nextMessages, data.message]);
    } catch (exc) {
      setError(exc.message);
    } finally {
      setIsSending(false);
    }
  }

  const theme = config?.theme || {};
  const accentColor = theme.accent_color || "#2563eb";

  return (
    <main className="widget-shell" ref={rootRef} style={{ "--accent-color": accentColor }}>
      <header className="widget-header">
        <strong>Maintainers Copilot</strong>
        <span>{config?.widget_id || widgetId}</span>
      </header>

      <section className="widget-messages" aria-live="polite">
        {messages.length === 0 && <p className="muted">{config?.greeting || "Loading widget…"}</p>}
        {messages.map((message, index) => (
          <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
            {message.content}
          </article>
        ))}
        {isSending && <p className="muted">Thinking…</p>}
        {error && <p className="error">{error}</p>}
      </section>

      <form className="widget-form" onSubmit={sendMessage}>
        <input
          aria-label="Message"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask a maintainer question…"
        />
        <button type="submit" disabled={isSending}>Send</button>
      </form>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);

export default App;
