import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { api } from "../lib/api";
import type { ViewerTarget } from "../types";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

type Props = {
  target: ViewerTarget;
  onClose: () => void;
};

type DocumentMeta = {
  rel_path?: string;
  pages?: number;
  status?: string;
};

type PageText = {
  text: string;
};

type ViewMode = "loading" | "pdf" | "text" | "error";

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export default function PdfViewer({ target, onClose }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [pdf, setPdf] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [mode, setMode] = useState<ViewMode>("loading");
  const [page, setPage] = useState(Math.max(1, target.page));
  const [pageInput, setPageInput] = useState(String(Math.max(1, target.page)));
  const [numPages, setNumPages] = useState(0);
  const [zoom, setZoom] = useState(1.2);
  const [error, setError] = useState<string | null>(null);
  const [textPage, setTextPage] = useState("");
  const [showExcerpt, setShowExcerpt] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let task: ReturnType<typeof pdfjsLib.getDocument> | null = null;

    setError(null);
    setPdf(null);
    setTextPage("");
    setMode("loading");
    const requested = Math.max(1, target.page);
    setPage(requested);
    setPageInput(String(requested));

    async function load() {
      try {
        const meta = await api<DocumentMeta>(`/api/documents/${target.documentId}`);
        if (cancelled) return;

        const isPdf = (meta.rel_path ?? "").trim().toLowerCase().endsWith(".pdf");
        const total = Math.max(1, meta.pages ?? requested);
        const initial = Math.min(requested, total);
        setPage(initial);
        setPageInput(String(initial));
        setNumPages(total);

        if (!isPdf) {
          setMode("text");
          return;
        }

        setMode("pdf");
        task = pdfjsLib.getDocument({
          url: `/api/documents/${target.documentId}/file`,
          withCredentials: true,
        });
        const doc = await task.promise;
        if (cancelled) {
          void doc.destroy();
          return;
        }
        setPdf(doc);
        setNumPages(doc.numPages);
        const initialPdfPage = Math.min(initial, doc.numPages);
        setPage(initialPdfPage);
        setPageInput(String(initialPdfPage));
      } catch (err) {
        if (!cancelled) {
          setError(errorText(err));
          setMode("error");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
      if (task) void task.destroy();
    };
  }, [target.documentId, target.page]);

  useEffect(() => {
    if (mode !== "text") return;
    let cancelled = false;
    setTextPage("");
    setError(null);
    api<PageText>(`/api/documents/${target.documentId}/pages/${page}`)
      .then((result) => {
        if (!cancelled) setTextPage(result.text);
      })
      .catch((err) => {
        if (!cancelled) setError(errorText(err));
      });
    return () => {
      cancelled = true;
    };
  }, [mode, page, target.documentId]);

  useEffect(() => {
    if (!pdf || !canvasRef.current) return;
    let cancelled = false;
    const canvas = canvasRef.current;
    pdf
      .getPage(page)
      .then((pdfPage) => {
        if (cancelled || !canvasRef.current) return;
        const dpr = window.devicePixelRatio || 1;
        const viewport = pdfPage.getViewport({ scale: zoom });
        const current = canvasRef.current;
        current.width = Math.floor(viewport.width * dpr);
        current.height = Math.floor(viewport.height * dpr);
        current.style.width = `${Math.floor(viewport.width)}px`;
        current.style.height = `${Math.floor(viewport.height)}px`;
        const context = current.getContext("2d");
        if (!context) return;
        return pdfPage
          .render({
            canvasContext: context,
            viewport,
            transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : undefined,
          })
          .promise.catch((err) => !cancelled && setError(errorText(err)));
      })
      .catch((err) => !cancelled && setError(errorText(err)));
    return () => {
      cancelled = true;
    };
  }, [pdf, page, zoom]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  function go(next: number) {
    if (!numPages) return;
    const clamped = Math.min(Math.max(1, next), numPages);
    setPage(clamped);
    setPageInput(String(clamped));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-3 backdrop-blur-sm sm:p-6">
      <div className="flex h-full max-h-[94vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl">
        <header className="flex flex-wrap items-center gap-3 border-b border-slate-200 px-4 py-2.5">
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-slate-800">{target.title}</div>
            <div className="text-xs text-slate-400">
              Document #{target.documentId}
              {mode === "text" && " · text-only source"}
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-600">
            <button
              type="button"
              onClick={() => go(page - 1)}
              disabled={page <= 1}
              className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50 disabled:opacity-40"
            >
              ‹
            </button>
            <input
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              onBlur={() => go(Number(pageInput) || page)}
              onKeyDown={(e) => e.key === "Enter" && go(Number(pageInput) || page)}
              className="w-12 rounded border border-slate-300 px-1 py-1 text-center outline-none focus:border-sky-500"
            />
            <span className="whitespace-nowrap">/ {numPages || "…"}</span>
            <button
              type="button"
              onClick={() => go(page + 1)}
              disabled={!numPages || page >= numPages}
              className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50 disabled:opacity-40"
            >
              ›
            </button>
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-600">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(0.6, +(z - 0.15).toFixed(2)))}
              disabled={mode !== "pdf"}
              className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50 disabled:opacity-40"
            >
              −
            </button>
            <span className="w-10 text-center">{Math.round(zoom * 100)}%</span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(2.6, +(z + 0.15).toFixed(2)))}
              disabled={mode !== "pdf"}
              className="rounded border border-slate-300 px-2 py-1 hover:bg-slate-50 disabled:opacity-40"
            >
              +
            </button>
          </div>
          {target.excerpt && (
            <button
              type="button"
              onClick={() => setShowExcerpt((v) => !v)}
              className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
            >
              {showExcerpt ? "Hide source text" : "Source text"}
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="rounded bg-slate-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-900"
          >
            Close
          </button>
        </header>
        <div className="flex min-h-0 flex-1">
          <div className="flex-1 overflow-auto bg-slate-100 p-4">
            {error ? (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
            ) : mode === "text" ? (
              <div className="mx-auto max-w-3xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Text source · page {page}
                </div>
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700">
                  {textPage || "Loading page text…"}
                </pre>
              </div>
            ) : (
              <div className="flex justify-center">
                <canvas
                  ref={canvasRef}
                  className={`rounded-sm bg-white shadow-md ${mode === "pdf" ? "" : "hidden"}`}
                />
              </div>
            )}
            {mode === "loading" && <div className="mt-4 text-center text-sm text-slate-400">Loading document…</div>}
            {mode === "pdf" && !pdf && !error && (
              <div className="mt-4 text-center text-sm text-slate-400">Loading PDF…</div>
            )}
          </div>
          {showExcerpt && target.excerpt && (
            <aside className="hidden w-80 shrink-0 overflow-y-auto border-l border-slate-200 bg-white p-4 text-sm text-slate-600 md:block">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Retrieved passage · p. {target.page}
              </div>
              <p className="whitespace-pre-wrap leading-relaxed">{target.excerpt}</p>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}
