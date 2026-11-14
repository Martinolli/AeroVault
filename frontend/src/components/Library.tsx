import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { LibraryDocument, ViewerTarget } from "../types";

const COLLECTIONS = [
  { id: "", label: "All collections" },
  { id: "Aviation HF", label: "Aviation Human Factors & Risk" },
  { id: "Quality ISO SAE", label: "Quality / ISO / SAE" },
  { id: "Aircraft Theory", label: "Aircraft Theory" },
];

const STATUS_STYLES: Record<string, string> = {
  indexed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  text_only: "bg-amber-50 text-amber-700 border-amber-200",
  partial: "bg-sky-50 text-sky-700 border-sky-200",
};

type Props = {
  onOpenDocument: (target: ViewerTarget) => void;
};

export default function Library({ onOpenDocument }: Props) {
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState("");
  const [documents, setDocuments] = useState<LibraryDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams({ limit: "300" });
      if (query.trim()) params.set("q", query.trim());
      if (collection) params.set("collection", collection);
      setLoading(true);
      setError(null);
      api<{ documents: LibraryDocument[]; count: number }>(`/api/library?${params.toString()}`)
        .then((data) => setDocuments(data.documents))
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query, collection]);

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-slate-200 bg-white/80 px-6 py-3 backdrop-blur">
        <h1 className="text-sm font-semibold text-slate-800">Library</h1>
        <p className="text-xs text-slate-500">
          Browse the indexed collection. Open any PDF in the built-in viewer.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-6 py-3">
        <div className="relative min-w-[16rem] flex-1">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by title or path…"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 outline-none ring-sky-500/30 focus:border-sky-500 focus:ring-2"
          />
        </div>
        <select
          value={collection}
          onChange={(e) => setCollection(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-sky-500"
        >
          {COLLECTIONS.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
        <div className="text-xs text-slate-500">
          {loading ? "Loading…" : `${documents.length} document${documents.length === 1 ? "" : "s"}`}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-6">
        {error && (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>
        )}
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full table-fixed divide-y divide-slate-100 text-sm">
            <colgroup>
              <col />
              <col className="w-44" />
              <col className="w-16" />
              <col className="w-24" />
            </colgroup>
            <thead className="bg-slate-50 text-left text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Title</th>
                <th className="px-4 py-2.5 font-semibold">Collection</th>
                <th className="px-4 py-2.5 text-right font-semibold">Pages</th>
                <th className="px-4 py-2.5 font-semibold">Index</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {documents.map((doc) => (
                <tr
                  key={doc.id}
                  onClick={() => onOpenDocument({ documentId: doc.id, title: doc.title, page: 1 })}
                  className="cursor-pointer transition hover:bg-sky-50/60"
                >
                  <td className="px-4 py-2.5">
                    <div className="truncate font-medium text-slate-800">{doc.title}</div>
                  </td>
                  <td className="truncate px-4 py-2.5 text-slate-500">{doc.collection}</td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-right tabular-nums text-slate-500">{doc.pages}</td>
                  <td className="whitespace-nowrap px-4 py-2.5">
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                        STATUS_STYLES[doc.status] ?? "border-slate-200 bg-slate-50 text-slate-600"
                      }`}
                    >
                      {doc.status}
                    </span>
                  </td>
                </tr>
              ))}
              {!loading && documents.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-slate-400">
                    No documents match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
