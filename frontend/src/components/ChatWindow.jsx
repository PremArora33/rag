import React, { useState, useRef, useEffect } from "react";
import { queryDocument } from "../utils/api";
import ReactMarkdown from "react-markdown";

const ConfidenceBadge = ({ level }) => {
  const map = { high: "#22c55e", medium: "#f59e0b", low: "#ef4444" };
  return (
    <span className="confidence-badge" style={{ borderColor: map[level], color: map[level] }}>
      {level} confidence
    </span>
  );
};

const HallucinationWarning = () => (
  <div className="hallucination-warning">
    ⚠ The document may not contain enough context for this question — answer reliability is reduced.
  </div>
);

const SourceCard = ({ source, index }) => (
  <div className="source-card">
    <div className="source-header">
      <span className="source-index">#{index + 1}</span>
      <span className="source-file">{source.file}</span>
      <span className="source-page">p.{source.page}</span>
      <span className="source-score" style={{ opacity: source.score }}>
        {Math.round(source.score * 100)}% match
      </span>
    </div>
    <p className="source-text">{source.text}</p>
  </div>
);

const Message = ({ msg, compareMode }) => {
  const [showSources, setShowSources] = useState(false);
  const [showComparison, setShowComparison] = useState(false);

  if (msg.role === "user") {
    return (
      <div className="message user-message">
        <div className="message-bubble user-bubble">
          <p>{msg.content}</p>
        </div>
      </div>
    );
  }

  if (msg.role === "loading") {
    return (
      <div className="message assistant-message">
        <div className="message-bubble assistant-bubble loading-bubble">
          <div className="typing-indicator">
            <span /><span /><span />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="message assistant-message">
      <div className="message-bubble assistant-bubble">
        {msg.is_hallucination_risk && <HallucinationWarning />}
        <div className="answer-content">
          <ReactMarkdown>{msg.rag_answer}</ReactMarkdown>
        </div>
        <div className="message-meta">
          <ConfidenceBadge level={msg.confidence} />
          <span className="reasoning-hint">{msg.reasoning}</span>
        </div>
        <div className="message-actions">
          {msg.sources?.length > 0 && (
            <button className="action-btn" onClick={() => setShowSources(!showSources)}>
              {showSources ? "Hide" : "View"} {msg.sources.length} sources
            </button>
          )}
          {compareMode && msg.plain_answer && (
            <button className="action-btn compare-btn" onClick={() => setShowComparison(!showComparison)}>
              {showComparison ? "Hide" : "Compare"} plain LLM answer
            </button>
          )}
        </div>
        {showSources && (
          <div className="sources-list">
            <p className="sources-title">Retrieved document chunks:</p>
            {msg.sources.map((s, i) => <SourceCard key={i} source={s} index={i} />)}
          </div>
        )}
        {showComparison && msg.plain_answer && (
          <div className="comparison-panel">
            <div className="comparison-header">
              <div className="comparison-label rag">RAG Answer (document-grounded)</div>
              <div className="comparison-label plain">Plain LLM Answer (general knowledge)</div>
            </div>
            <div className="comparison-body">
              <div className="comparison-col rag-col">
                <ReactMarkdown>{msg.rag_answer}</ReactMarkdown>
              </div>
              <div className="comparison-col plain-col">
                <ReactMarkdown>{msg.plain_answer}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default function ChatWindow({ compareMode }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }, { role: "loading" }]);
    setLoading(true);

    try {
      const result = await queryDocument(question, compareMode);
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", ...result };
        return updated;
      });
    } catch (e) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          rag_answer: "Error: " + (e.response?.data?.detail || e.message),
          confidence: "low",
          sources: [],
          is_hallucination_risk: false,
          reasoning: "",
        };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div className="chat-window">
      <div className="messages-area">
        {messages.length === 0 && (
          <div className="empty-chat">
            <p>Ask anything about your document</p>
            <div className="sample-questions">
              {["Summarize this document", "What are the key findings?", "List the main topics covered"].map((q) => (
                <button key={q} className="sample-q" onClick={() => { setInput(q); }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} compareMode={compareMode} />
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="input-area">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask a question about your document… (Enter to send)"
          rows={2}
          disabled={loading}
        />
        <button className="send-btn" onClick={send} disabled={loading || !input.trim()}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  );
}
