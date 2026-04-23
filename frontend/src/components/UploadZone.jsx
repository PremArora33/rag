import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { uploadPDF } from "../utils/api";

export default function UploadZone({ onUploaded }) {
  const [status, setStatus] = useState(null); // null | 'uploading' | 'success' | 'error'
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");

  const onDrop = useCallback(async (accepted) => {
    const file = accepted[0];
    if (!file) return;
    setStatus("uploading");
    setError("");
    try {
      const result = await uploadPDF(file);
      setInfo(result);
      setStatus("success");
      onUploaded(result);
    } catch (e) {
      setError(e.response?.data?.detail || "Upload failed");
      setStatus("error");
    }
  }, [onUploaded]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
    maxSize: 10 * 1024 * 1024,
  });

  return (
    <div className="upload-zone-wrapper">
      <div
        {...getRootProps()}
        className={`upload-zone ${isDragActive ? "drag-active" : ""} ${status === "success" ? "uploaded" : ""}`}
      >
        <input {...getInputProps()} />
        {status === "uploading" && (
          <div className="upload-state">
            <div className="spinner" />
            <p>Processing PDF…</p>
          </div>
        )}
        {status === "success" && info && (
          <div className="upload-state success">
            <div className="check-icon">✓</div>
            <p className="filename">{info.message}</p>
            <p className="meta">{info.pages} pages · {info.chunks} chunks indexed</p>
            <p className="hint">Drop another PDF to add more documents</p>
          </div>
        )}
        {status === "error" && (
          <div className="upload-state error">
            <p>⚠ {error}</p>
          </div>
        )}
        {!status && (
          <div className="upload-state">
            <div className="upload-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="12" y1="18" x2="12" y2="12" />
                <line x1="9" y1="15" x2="15" y2="15" />
              </svg>
            </div>
            <p className="primary-text">{isDragActive ? "Drop it here" : "Drop your PDF here"}</p>
            <p className="secondary-text">or click to browse · max 10MB</p>
          </div>
        )}
      </div>
    </div>
  );
}
