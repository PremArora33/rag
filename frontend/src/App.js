import React, { useState, useEffect } from "react";
import UploadZone from "./components/UploadZone";
import ChatWindow from "./components/ChatWindow";
import { getStats, clearDocuments } from "./utils/api";
import "./App.css";

export default function App() {
  const [docReady, setDocReady] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [stats, setStats] = useState(null);

  const refreshStats = async () => {
    try {
      const s = await getStats();
      setStats(s);
    } catch {}
  };

  const handleUploaded = () => {
    setDocReady(true);
    refreshStats();
  };

  const handleClear = async () => {
    await clearDocuments();
    setDocReady(false);
    setStats(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-icon">◈</span>
            <span className="logo-text">DocMind</span>
            <span className="logo-tag">RAG</span>
          </div>
          <p className="tagline">Grounded answers from your documents · Powered by Groq + LLaMA 3.3</p>
        </div>
        <div className="header-right">
          {docReady && (
            <>
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={compareMode}
                  onChange={(e) => setCompareMode(e.target.checked)}
                />
                <span className="toggle-text">Compare mode</span>
              </label>
              <button className="clear-btn" onClick={handleClear}>Clear docs</button>
            </>
          )}
        </div>
      </header>

      {stats && (
        <div className="stats-bar">
          <span>{stats.total_chunks} chunks indexed</span>
          {stats.documents.map((d, i) => (
            <span key={i} className="stat-doc">📄 {d.filename} ({d.pages}p)</span>
          ))}
        </div>
      )}

      <main className="app-main">
        <div className={`left-panel ${docReady ? "compact" : ""}`}>
          <UploadZone onUploaded={handleUploaded} />
          {!docReady && (
            <div className="how-it-works">
              <h3>How it works</h3>
              <ol>
                <li><strong>Upload</strong> any PDF document</li>
                <li><strong>Ask</strong> questions in natural language</li>
                <li><strong>Get answers</strong> grounded in your document</li>
                <li><strong>Compare</strong> RAG vs plain LLM to see the difference</li>
              </ol>
              <div className="tech-stack">
                <span>FastAPI</span>
                <span>LangChain</span>
                <span>FAISS</span>
                <span>Groq</span>
                <span>LLaMA 3.3</span>
              </div>
            </div>
          )}
        </div>

        <div className={`right-panel ${!docReady ? "disabled" : ""}`}>
          {!docReady && (
            <div className="chat-placeholder">
              <p>Upload a document to start asking questions</p>
            </div>
          )}
          {docReady && <ChatWindow compareMode={compareMode} />}
        </div>
      </main>

      {compareMode && (
        <div className="compare-banner">
          Compare mode ON — answers will show RAG (document-grounded) vs plain LLM side by side
        </div>
      )}
    </div>
  );
}
