import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { notifyParentOfHeight } from "./postMessage.js";
import { fetchWidgetConfig } from "./useWidgetConfig.js";
import "./style.css";

const TOOL_LABELS = {
  rag_search: "Retrieval",
  classify_issue: "Classifier",
  extract_entities: "Entities",
  summarize_issue: "Summarizer",
};

function queryParam(name, fallback) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) || fallback;
}

function enabledTools(config) {
  if (!config || !Array.isArray(config.enabled_tools)) return [];
  return config.enabled_tools;
}

function friendlyError(message) {
  if (message.includes("HTTP 403")) {
    return "This host is not allowed to use the widget. Ask an admin to add this origin in Widget config.";
  }
  if (message.includes("HTTP 404")) {
    return "Widget config is missing. Ask an admin to save the default widget config.";
  }
  return message;
}

async function readSse(response, onEvent) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Streaming is not available in this browser.");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const event = parseSseBlock(block);
      if (event) onEvent(event);
      boundary = buffer.indexOf("\n\n");
    }
  }

  if (buffer.trim()) {
    const event = parseSseBlock(buffer);
    if (event) onEvent(event);
  }
}

function parseSseBlock(block) {
  let event = "message";
  const dataLines = [];
  for (const rawLine of block.split("\n")) {
    const line = rawLine.trimEnd();
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return null;
  return { event, data: JSON.parse(dataLines.join("\n")) };
}

function toolLabel(name) {
  const labels = {
    "rag.query": "Retrieval",
    "classifier.classify": "Classifier",
    "ner.extract": "Entities",
    "summarizer.summarize": "Summarizer",
    "memory.write": "Memory",
  };
  return labels[name] || name;
}

function toolDetail(tool) {
  if (tool.name === "rag.query") {
    return `${tool.chunks?.length || 0} chunks`;
  }
  if (tool.name === "classifier.classify") {
    const label = tool.metadata?.label || "unknown";
    const confidence = tool.metadata?.confidence;
    return typeof confidence === "number" ? `${label} at ${Math.round(confidence * 100)}%` : label;
  }
  if (tool.name === "ner.extract") {
    const grouped = tool.metadata?.grouped || {};
    const count = Object.values(grouped).reduce(
      (total, values) => total + (Array.isArray(values) ? values.length : 0),
      0,
    );
    return `${count} entities`;
  }
  return tool.status || "ok";
}

function uniqueCitations(toolResults) {
  const citations = [];
  for (const tool of toolResults) {
    for (const citation of tool.citations || []) {
      if (!citations.includes(citation)) citations.push(citation);
    }
  }
  return citations;
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
  const [toolResults, setToolResults] = useState([]);
  const rootRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    fetchWidgetConfig({ apiBase, widgetId, hostOrigin })
      .then(setConfig)
      .catch((exc) => setError(friendlyError(exc.message)));
  }, [apiBase, widgetId, hostOrigin]);

  useEffect(() => {
    if (rootRef.current) notifyParentOfHeight(rootRef.current.scrollHeight + 24);
  }, [config, messages, error, isSending, toolResults]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, toolResults, isSending]);

  async function sendMessage(event) {
    event.preventDefault();
    const content = input.trim();
    if (!content || isSending) return;

    const userMessage = { role: "user", content };
    const requestMessages = [...messages, userMessage];
    setMessages([...requestMessages, { role: "assistant", content: "" }]);
    setInput("");
    setIsSending(true);
    setError("");
    setToolResults([]);

    try {
      const response = await fetch(
        `${apiBase}/widget/${encodeURIComponent(widgetId)}/chat/stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Widget-Origin": hostOrigin,
          },
          body: JSON.stringify({
            conversation_id: conversationId,
            messages: requestMessages,
            use_rag: enabledTools(config).includes("rag_search"),
            top_k: 5,
            allow_summarizer: enabledTools(config).includes("summarize_issue"),
            allow_memory_write: false,
            tools: ["auto"],
          }),
        },
      );
      if (!response.ok) throw new Error(`Chat failed with HTTP ${response.status}`);

      let assistantText = "";
      await readSse(response, ({ event: eventName, data }) => {
        if (eventName === "metadata") {
          setConversationId(data.conversation_id);
        }
        if (eventName === "tool_result") {
          setToolResults((current) => [...current, data]);
        }
        if (eventName === "delta") {
          assistantText += data.content || "";
          setMessages([...requestMessages, { role: "assistant", content: assistantText }]);
        }
        if (eventName === "final") {
          setConversationId(data.conversation_id);
          assistantText = data.message?.content || assistantText;
          setMessages([...requestMessages, { role: "assistant", content: assistantText }]);
          setToolResults(data.tool_results || []);
        }
        if (eventName === "error") {
          throw new Error(data.message || "Chat request failed.");
        }
      });
    } catch (exc) {
      setMessages(requestMessages);
      setError(friendlyError(exc.message));
    } finally {
      setIsSending(false);
    }
  }

  function usePrompt(value) {
    setInput(value);
  }

  function handleComposerKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      sendMessage(event);
    }
  }

  const theme = config?.theme || {};
  const accentColor = theme.accent_color || "#16a34a";
  const themeMode = theme.mode === "dark" ? "dark" : "light";
  const tools = enabledTools(config);
  const canSend = Boolean(config) && tools.length > 0 && !isSending;
  const statusText = config ? "Ready" : "Connecting";
  const citations = uniqueCitations(toolResults);

  return (
    <main
      className={`widget-shell ${themeMode}`}
      ref={rootRef}
      style={{ "--accent-color": accentColor }}
    >
      <header className="widget-header">
        <div className="brand">
          <span className="brand-mark">MC</span>
          <span>
            <strong>Maintainers Copilot</strong>
            <small>{widgetId}</small>
          </span>
        </div>
        <span className="status-pill">{statusText}</span>
      </header>

      <section className="tool-strip" aria-label="Enabled tools">
        {tools.length > 0 ? (
          tools.map((tool) => <span key={tool}>{TOOL_LABELS[tool] || tool}</span>)
        ) : (
          <span>No tools enabled</span>
        )}
      </section>

      <section className="widget-messages" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>{config?.greeting || "Loading widget configuration..."}</p>
            <div className="prompt-grid">
              <button
                type="button"
                onClick={() => usePrompt("Use RAG to find context for pandas read_csv empty-file crashes.")}
              >
                Find context
              </button>
              <button
                type="button"
                onClick={() =>
                  usePrompt("Classify this issue: read_csv crashes on empty CSV with ValueError.")
                }
              >
                Triage issue
              </button>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
            {message.content || (message.role === "assistant" ? "Thinking..." : "")}
          </article>
        ))}

        {toolResults.length > 0 && (
          <section className="evidence-panel" aria-label="Tool results">
            <div className="evidence-header">
              <strong>Evidence</strong>
              <span>{toolResults.length} tool calls</span>
            </div>
            <div className="tool-grid">
              {toolResults.map((tool, index) => (
                <div className="tool-result" key={`${tool.name}-${index}`}>
                  <strong>{toolLabel(tool.name)}</strong>
                  <span>{toolDetail(tool)}</span>
                </div>
              ))}
            </div>
            {citations.length > 0 && (
              <div className="citation-list">
                {citations.slice(0, 4).map((citation) => (
                  <span key={citation}>{citation}</span>
                ))}
              </div>
            )}
            {toolResults.some((tool) => tool.chunks?.length) && (
              <details className="chunk-details">
                <summary>Retrieved chunks</summary>
                {toolResults.flatMap((tool) =>
                  (tool.chunks || []).slice(0, 3).map((chunk) => (
                    <article key={chunk.chunk_id}>
                      <strong>{chunk.parent_title || chunk.title || chunk.source_id}</strong>
                      <p>{chunk.text_preview}</p>
                    </article>
                  )),
                )}
              </details>
            )}
          </section>
        )}

        {isSending && <p className="muted">Working through the tools...</p>}
        {error && <p className="error">{error}</p>}
        <div ref={endRef} />
      </section>

      <form className="widget-form" onSubmit={sendMessage}>
        <textarea
          aria-label="Message"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleComposerKeyDown}
          placeholder="Ask about an issue or project context"
          rows="2"
          disabled={!config || tools.length === 0}
        />
        <button type="submit" disabled={!canSend || !input.trim()}>
          Send
        </button>
      </form>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);

export default App;
