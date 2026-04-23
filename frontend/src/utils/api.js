import axios from "axios";

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000",
});

export const uploadPDF = async (file) => {
  const form = new FormData();
  form.append("file", file);
  const res = await API.post("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const queryDocument = async (question, compareMode = false) => {
  const res = await API.post("/query", {
    question,
    compare_mode: compareMode,
  });
  return res.data;
};

export const getHealth = async () => {
  const res = await API.get("/health");
  return res.data;
};

export const getStats = async () => {
  const res = await API.get("/stats");
  return res.data;
};

export const clearDocuments = async () => {
  const res = await API.delete("/documents");
  return res.data;
};

export const queryStream = (question, onToken, onDone) => {
  const url = `${process.env.REACT_APP_API_URL || "http://localhost:8000"}/query/stream`;

  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  }).then((res) => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    const read = () => {
      reader.read().then(({ done, value }) => {
        if (done) return;
        const text = decoder.decode(value);
        const lines = text.split("\n").filter((l) => l.startsWith("data: "));
        lines.forEach((line) => {
          const data = line.replace("data: ", "");
          if (data === "[DONE]") { onDone(); return; }
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === "token") onToken(parsed.content);
            if (parsed.type === "done") onDone();
          } catch {}
        });
        read();
      });
    };
    read();
  });
};
