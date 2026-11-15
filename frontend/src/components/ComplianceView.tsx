import { useEffect, useState } from "react";
import { api, downloadCompliance, uploadCompliance } from "../lib/api";
import type {
  ComplianceClause,
  ComplianceResult,
  ComplianceRun,
  StandardDocument,
  ViewerTarget,
} from "../types";

type Props = { onOpenSource: (target: ViewerTarget) => void };
type Stage = "upload" | "setup" | "running" | "results";

const STATUS_STYLE: Record<string, string> = {
  Compliant: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Partial: "bg-amber-50 text-amber-700 border-amber-200",
  Gap: "bg-rose-50 text-rose-700 border-rose-200",
  "Not applicable": "bg-slate-100 text-slate-600 border-slate-200",
  Unclear: "bg-sky-50 text-sky-700 border-sky-200",
};

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : "Unexpected error";
}

export default function ComplianceView({ onOpenSource }: Props) {
  const [stage, setStage] = useState<Stage>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [ocr, setOcr] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [filename, setFilename] = useState("");
  const [clauses, setClauses] = useState<ComplianceClause[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [standards, setStandards] = useState<StandardDocument[]>([]);
  const [stdQuery, setStdQuery] = useState("AS9100");
  const [selected, setSelected] = useState<StandardDocument[]>([]);
  const [model, setModel] = useState("gpt-4o-mini");
  const [extra, setExtra] = useState<string[]>(["", "", ""]);
  const [instructions, setInstructions] = useState("");
  const [run, setRun] = useState<ComplianceRun | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    const timer = window.setTimeout(async () => {
      try {
        const data = await api<{ standards: StandardDocument[] }>(
          `/api/compliance/standards?q=${encodeURIComponent(stdQuery)}`,
        );
        if (alive) setStandards(data.standards);
      } catch {
        /* non-critical */
      }
    }, 250);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [stdQuery]);

  useEffect(() => {
    if (stage !== "running" || !runId) return;
    const timer = window.setInterval(async () => {
      try {
        const data = await api<ComplianceRun>(`/api/compliance/${runId}`);
        setRun(data);
        if (data.status === "done") setStage("results");
        else if (data.status === "error" || data.status === "cancelled") {
          setStage("setup");
          setError(data.error || "The run was cancelled.");
        }
      } catch {
        /* keep polling */
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [stage, runId]);

  function reset() {
    setStage("upload");
    setFile(null);
    setRunId(null);
    setFilename("");
    setClauses([]);
    setWarnings([]);
    setSelected([]);
    setRun(null);
    setError("");
    setInstructions("");
    setExtra(["", "", ""]);
  }

  async function onUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const data = await uploadCompliance(file, ocr);
      setRunId(data.run_id);
      setFilename(data.filename);
      setClauses(data.clauses);
      setWarnings(data.warnings);
      setStage("setup");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  function toggleStandard(doc: StandardDocument) {
    setSelected((prev) =>
      prev.some((s) => s.id === doc.id) ? prev.filter((s) => s.id !== doc.id) : [...prev, doc],
    );
  }

  async function startRun() {
    if (!runId || selected.length === 0) {
      setError("Select at least one standard.");
      return;
    }
    if (clauses.length === 0) {
      setError("Add at least one clause.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const data = await api<ComplianceRun>(`/api/compliance/${runId}/run`, {
        method: "POST",
        body: JSON.stringify({
          standard_ids: selected.map((s) => s.id),
          model,
          clauses,
          extra_columns: extra.filter((x) => x.trim()),
          instructions,
        }),
      });
      setRun(data);
      setStage("running");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function cancelRun() {
    if (!runId) return;
    try {
      await api(`/api/compliance/${runId}/cancel`, { method: "POST" });
      setStage("setup");
    } catch (err) {
      setError(errorText(err));
    }
  }

  const counts = (run?.results ?? []).reduce<Record<string, number>>((acc, r) => {
    acc[r.status] = (acc[r.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-5 py-6">
        <div className="mb-5">
          <h1 className="text-xl font-semibold text-slate-800">Compliance workspace</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            Upload a procedure, choose the standard(s) named in your request, and compare it clause by clause.
            Uploads are transient: they are not stored in the library or indexed.
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {stage === "upload" && (
          <form onSubmit={onUpload} className="max-w-2xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <label className="block text-sm font-medium text-slate-700">
              Procedure file (PDF or DOCX)
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="mt-2 block w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm"
              />
            </label>
            <label className="mt-4 flex items-start gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={ocr} onChange={(e) => setOcr(e.target.checked)} className="mt-0.5" />
              <span>
                OCR scanned pages (slower, uses Tesseract). Leave off for text PDFs and DOCX files.
              </span>
            </label>
            <button
              type="submit"
              disabled={!file || busy}
              className="mt-5 rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
            >
              {busy ? "Reading procedure…" : "Upload and detect clauses"}
            </button>
          </form>
        )}

        {stage === "setup" && (
          <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-800">Detected clauses</h2>
                  <p className="text-xs text-slate-400">{filename} · {clauses.length} clause(s)</p>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setClauses((prev) => [...prev, { id: String(prev.length + 1), heading: "", text: "" }])
                  }
                  className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  + Add clause
                </button>
              </div>
              {warnings.length > 0 && (
                <div className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
                  {warnings.join(" ")}
                </div>
              )}
              <div className="mt-4 max-h-[55vh] space-y-3 overflow-y-auto pr-1">
                {clauses.map((clause, idx) => (
                  <div key={`${clause.id}-${idx}`} className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-white px-1.5 py-0.5 text-[11px] font-semibold text-slate-500">
                        {clause.id}
                      </span>
                      <input
                        value={clause.heading}
                        onChange={(e) =>
                          setClauses((prev) =>
                            prev.map((c, i) => (i === idx ? { ...c, heading: e.target.value } : c)),
                          )
                        }
                        placeholder="Clause heading"
                        className="min-w-0 flex-1 rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium"
                      />
                      <button
                        type="button"
                        aria-label="Remove clause"
                        onClick={() => setClauses((prev) => prev.filter((_, i) => i !== idx))}
                        className="rounded px-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                      >
                        ×
                      </button>
                    </div>
                    <textarea
                      value={clause.text}
                      onChange={(e) =>
                        setClauses((prev) =>
                          prev.map((c, i) => (i === idx ? { ...c, text: e.target.value } : c)),
                        )
                      }
                      rows={3}
                      className="mt-2 w-full resize-y rounded border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700"
                    />
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-4">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-800">Standard(s) for this request</h2>
                <p className="mt-1 text-xs text-slate-400">
                  Search and select the standards you named, e.g. AS9100D, ISO 9001.
                </p>
                <input
                  value={stdQuery}
                  onChange={(e) => setStdQuery(e.target.value)}
                  placeholder="Search standards…"
                  className="mt-3 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:bg-white"
                />
                <div className="mt-2 max-h-44 space-y-1 overflow-y-auto">
                  {standards.map((doc) => {
                    const active = selected.some((s) => s.id === doc.id);
                    return (
                      <button
                        type="button"
                        key={doc.id}
                        onClick={() => toggleStandard(doc)}
                        className={`flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition ${
                          active ? "bg-sky-50 text-sky-800" : "hover:bg-slate-50 text-slate-600"
                        }`}
                      >
                        <span className={`mt-0.5 h-3 w-3 shrink-0 rounded border ${active ? "border-sky-600 bg-sky-600" : "border-slate-300"}`} />
                        <span className="min-w-0">
                          <span className="block truncate font-medium">{doc.title}</span>
                          <span className="text-[11px] text-slate-400">{doc.collection} · {doc.pages} pp · {doc.status}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
                {selected.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {selected.map((s) => (
                      <button
                        type="button"
                        key={s.id}
                        onClick={() => toggleStandard(s)}
                        className="rounded-full bg-sky-100 px-2.5 py-1 text-[11px] font-medium text-sky-800"
                        title="Remove"
                      >
                        {s.title.slice(0, 45)} ×
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-800">Analysis options</h2>
                <label className="mt-3 block text-xs font-medium text-slate-500">
                  Model
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-sm"
                  >
                    <option value="gpt-4o-mini">gpt-4o-mini · fast</option>
                    <option value="gpt-4o">gpt-4o · deeper</option>
                  </select>
                </label>
                <div className="mt-3">
                  <div className="text-xs font-medium text-slate-500">Extra columns (optional, max 3)</div>
                  {extra.map((value, i) => (
                    <input
                      key={i}
                      value={value}
                      onChange={(e) => setExtra((prev) => prev.map((x, j) => (j === i ? e.target.value : x)))}
                      placeholder={["e.g. Risk rating", "e.g. Action owner", "e.g. Due date"][i]}
                      className="mt-1.5 w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs"
                    />
                  ))}
                </div>
                <label className="mt-3 block text-xs font-medium text-slate-500">
                  Request / instructions (optional)
                  <textarea
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    rows={3}
                    placeholder="e.g. Compare against AS9100D clause 7 and flag training records gaps."
                    className="mt-1 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => void startRun()}
                  disabled={busy || selected.length === 0}
                  className="mt-4 w-full rounded-lg bg-sky-700 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
                >
                  {busy ? "Starting…" : `Run compliance check (${clauses.length} clauses)`}
                </button>
                <button type="button" onClick={reset} className="mt-2 w-full text-xs text-slate-400 hover:text-slate-600">
                  Start over
                </button>
              </div>
            </section>
          </div>
        )}

        {stage === "running" && run && (
          <div className="max-w-3xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">Analysing clauses…</h2>
                <p className="text-xs text-slate-400">
                  {run.progress} of {run.total} · {run.model}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void cancelRun()}
                className="rounded-md border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50"
              >
                Cancel
              </button>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-sky-600 transition-all"
                style={{ width: `${run.total ? (run.progress / run.total) * 100 : 0}%` }}
              />
            </div>
            <div className="mt-4 space-y-2">
              {run.results.map((r) => (
                <div key={r.clause_id} className="flex items-center gap-2 text-xs">
                  <span className={`rounded-full border px-2 py-0.5 font-medium ${STATUS_STYLE[r.status]}`}>{r.status}</span>
                  <span className="truncate text-slate-600">{r.clause_heading || r.clause_excerpt}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {stage === "results" && run && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">{filename} · compliance matrix</h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  {run.results.length} clause(s) · {Object.entries(counts).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => void downloadCompliance(run.run_id, "xlsx", filename.replace(/\.[^.]+$/, ""))}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  Export XLSX
                </button>
                <button
                  type="button"
                  onClick={() => void downloadCompliance(run.run_id, "docx", filename.replace(/\.[^.]+$/, ""))}
                  className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  Export DOCX
                </button>
                <button
                  type="button"
                  onClick={reset}
                  className="rounded-lg bg-sky-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-800"
                >
                  New analysis
                </button>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
              <table className="min-w-[900px] w-full text-left text-xs">
                <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Clause</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Requirement</th>
                    <th className="px-3 py-2">Standard / page</th>
                    <th className="px-3 py-2">Action</th>
                    {run.extra_columns.map((c) => <th key={c} className="px-3 py-2">{c}</th>)}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {run.results.map((r: ComplianceResult) => (
                    <tr key={r.clause_id} className="align-top hover:bg-slate-50/60">
                      <td className="max-w-[220px] px-3 py-2">
                        <div className="font-medium text-slate-700">{r.clause_heading || `Clause ${r.clause_id}`}</div>
                        <div className="mt-0.5 line-clamp-2 text-[11px] text-slate-400">{r.clause_excerpt}</div>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-block rounded-full border px-2 py-0.5 font-medium ${STATUS_STYLE[r.status]}`}>{r.status}</span>
                        <div className="mt-1 text-[10px] text-slate-400">{r.confidence} confidence</div>
                      </td>
                      <td className="max-w-[260px] px-3 py-2 text-slate-600">
                        <div>{r.requirement}</div>
                        <div className="mt-1 text-[11px] italic text-slate-400">{r.rationale}</div>
                      </td>
                      <td className="max-w-[180px] px-3 py-2 text-slate-600">
                        <div className="truncate">{r.standard || "—"}</div>
                        {r.document_id > 0 && (
                          <button
                            type="button"
                            onClick={() =>
                              onOpenSource({ documentId: r.document_id, title: r.standard, page: r.page, excerpt: r.evidence })
                            }
                            className="mt-1 text-[11px] font-medium text-sky-700 hover:underline"
                          >
                            Open p.{r.page}
                          </button>
                        )}
                      </td>
                      <td className="max-w-[240px] px-3 py-2 text-slate-600">{r.action || "—"}</td>
                      {run.extra_columns.map((c) => (
                        <td key={c} className="px-3 py-2 text-slate-500">{r.extras?.[c] || ""}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-slate-400">
              Decision-support output. Verify every finding against the cited standard page before use.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
