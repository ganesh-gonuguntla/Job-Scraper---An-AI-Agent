const API_BASE = "/api";

export async function startRun(file, preferences) {
  const formData = new FormData();
  if (file) {
    formData.append("pdf", file);
  }
  formData.append("preferences", JSON.stringify(preferences));

  const resp = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    body: formData,
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Failed to start job search run: ${errText}`);
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
  const resp = await fetch(`${API_BASE}/runs/${runId}/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile, queries }),
  });

  if (!resp.ok) {
    throw new Error("Failed to resume run");
  }
  return await resp.json();
}

export async function rerankJobs(runId, preferences) {
  const resp = await fetch(`${API_BASE}/runs/${runId}/rerank`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences),
  });

  if (!resp.ok) {
    throw new Error("Failed to rerank jobs");
  }
  return await resp.json();
}
