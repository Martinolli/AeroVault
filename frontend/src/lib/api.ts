import type { Source } from "../types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* keep status text */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

type StreamHandlers = {
  onSources: (sources: Source[]) => void;
  onDelta: (delta: string) => void;
  onDone: (payload: { chat_id: number; message_id: number }) => void;
  onError: (detail: string) => void;
};

export async function streamChat(
  payload: { question: string; chat_id: number | null; model: string },
  handlers: StreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let split = buffer.indexOf("\n\n");
    while (split >= 0) {
      const block = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      split = buffer.indexOf("\n\n");
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (!data) continue;
      let parsed: any;
      try {
        parsed = JSON.parse(data);
      } catch {
        continue;
      }
      if (event === "sources") handlers.onSources(parsed.sources ?? []);
      else if (event === "delta") handlers.onDelta(parsed.delta ?? "");
      else if (event === "done") handlers.onDone(parsed);
      else if (event === "error") handlers.onError(parsed.detail ?? "Unknown error");
    }
  }
}

export type ComplianceUpload = {
  run_id: string;
  filename: string;
  clauses: { id: string; heading: string; text: string }[];
  warnings: string[];
};

export async function uploadCompliance(file: File, ocr: boolean): Promise<ComplianceUpload> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("ocr", String(ocr));
  const res = await fetch("/api/compliance/upload", {
    method: "POST",
    credentials: "include",
    body: fd,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as ComplianceUpload;
}

export async function downloadCompliance(runId: string, format: "docx" | "xlsx", fallback: string) {
  const res = await fetch(`/api/compliance/${runId}/export.${format}`, { credentials: "include" });
  if (!res.ok) throw new ApiError(`Export failed (HTTP ${res.status})`, res.status);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${fallback}_compliance.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

export function formatDate(iso: string): string {
  if (!iso) return "";
  const date = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  if (Number.isNaN(date.getTime())) return iso.slice(0, 10);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
