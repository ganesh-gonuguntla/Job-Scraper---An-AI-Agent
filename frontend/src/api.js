const rawApiBase = import.meta.env.VITE_API_BASE_URL || "/api";
const API_BASE = rawApiBase.replace(/\/+$/, "");

export async function getConfig() {
  try {
    const resp = await fetch(`${API_BASE}/config`);
    if (resp.ok) {
      return await resp.json();
    }
  } catch (err) {
    console.debug("Config fetch error:", err);
  }
  return {
    status: "ok",
    llm_provider: "Groq Llama 3",
    llm_healthy: true,
    job_sources: "JSearch + Live Job Boards",
    sources_healthy: true,
  };
}

export async function startRun(file, preferences) {
  const formData = new FormData();
  if (file) {
    formData.append("pdf", file);
  }
  formData.append("preferences", JSON.stringify(preferences));

  let resp;
  try {
    resp = await fetch(`${API_BASE}/runs`, {
      method: "POST",
      body: formData,
    });
  } catch (err) {
    throw new Error(
      "Cannot connect to the backend server at http://127.0.0.1:8000. Please ensure the backend is running (run: uvicorn backend.api:app --reload)."
    );
  }

  if (!resp.ok) {
    let errMsg = `Server returned status ${resp.status}`;
    try {
      const errJson = await resp.json();
      if (errJson && errJson.detail) {
        errMsg = errJson.detail;
      }
    } catch {
      const errText = await resp.text();
      if (errText) errMsg = errText;
    }
    throw new Error(errMsg);
  }

  return await resp.json();
}

export function subscribeRunStream(runId, { onNodeStart, onNodeEnd, onInterrupt, onResult, onError, onComplete }) {
  const eventSource = new EventSource(`${API_BASE}/runs/${runId}/stream`);

  eventSource.addEventListener("node_start", (e) => {
    try {
      const data = JSON.parse(e.data);
      onNodeStart?.(data);
    } catch (err) {
      console.error("Error parsing node_start:", err);
    }
  });

  eventSource.addEventListener("node_end", (e) => {
    try {
      const data = JSON.parse(e.data);
      onNodeEnd?.(data);
    } catch (err) {
      console.error("Error parsing node_end:", err);
    }
  });

  eventSource.addEventListener("interrupt", (e) => {
    try {
      const data = JSON.parse(e.data);
      onInterrupt?.(data);
    } catch (err) {
      console.error("Error parsing interrupt:", err);
    }
  });

  eventSource.addEventListener("result", (e) => {
    try {
      const data = JSON.parse(e.data);
      onResult?.(data);
    } catch (err) {
      console.error("Error parsing result:", err);
    }
    eventSource.close();
    onComplete?.();
  });

  eventSource.addEventListener("error", (e) => {
    try {
      if (e.data) {
        const data = JSON.parse(e.data);
        onError?.(data.message || "An unexpected error occurred during processing");
      }
    } catch (err) {
      // Stream closed or transport error
    }
  });

  eventSource.onerror = (err) => {
    console.warn("EventSource closed or reconnecting", err);
  };

  return () => {
    eventSource.close();
  };
}

export async function resumeRun(runId, { profile, queries }) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}/runs/${runId}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile, queries }),
    });
  } catch (err) {
    throw new Error("Cannot connect to backend server at http://127.0.0.1:8000.");
  }

  if (!resp.ok) {
    throw new Error("Failed to resume run");
  }
  return await resp.json();
}

export async function rerankJobs(runId, preferences) {
  let resp;
  try {
    resp = await fetch(`${API_BASE}/runs/${runId}/rerank`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(preferences),
    });
  } catch (err) {
    throw new Error("Cannot connect to backend server at http://127.0.0.1:8000.");
  }

  if (!resp.ok) {
    throw new Error("Failed to rerank jobs");
  }
  return await resp.json();
}

export const getApiConfig = getConfig;
