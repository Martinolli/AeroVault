import { useEffect, useState } from "react";
import {
  api,
  downloadCompliance,
  formatDate,
  libraryCompliance,
  uploadCompliance,
} from "../lib/api";
import type {
  ComplianceClause,
  ComplianceHistoryItem,
  ComplianceMode,
  ComplianceNarrative,
  ComplianceResult,
  ComplianceRun,
  StandardDocument,
  ViewerTarget,
} from "../types";

type Props = { onOpenSource: (target: ViewerTarget) => void };
type Stage = "input" | "setup" | "running" | "results";
type InputKind = "upload" | "library";

const STATUS_STYLE: Record<string, string> = {
  Compliant: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Partial: "bg-amber-50 text-amber-700 border-amber-200",
  Gap: "bg-rose-50 text-rose-700 border-rose-200",
  "Not applicable": "bg-slate-100 text-slate-600 border-slate-200",
  Unclear: "bg-sky-50 text-sky-700 border-sky-200",
};

const SEVERITY_STYLE: Record<string, string> = {
  High: "bg-rose-50 text-rose-700 border-rose-200",
  Medium: "bg-amber-50 text-amber-700 border-amber-200",
  Low: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const AUTHORITIES = ["FAA", "EASA", "ICAO", "AQAP", "NASA", "BOOKS"];

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : "Unexpected error";
}

function modeLabel(mode: ComplianceMode): string {
  if (mode === "gap") return "Gap / coverage review";
  if (mode === "improvement") return "Improvement review";
  return "Problem-driven analysis";
}

export default function ComplianceView({ onOpenSource }: Props) {
  const [stage, setStage] = useState<Stage>("input");
  const [inputKind, setInputKind] = useState<InputKind>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [ocr, setOcr] = useState(false);
  const [libraryQuery, setLibraryQuery] = useState("");
  const [libraryDocs, setLibraryDocs] = useState<StandardDocument[]>([]);
  const [libraryDoc, setLibraryDoc] = useState<StandardDocument | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const [filename, setFilename] = useState("");
  const [clauses, setClauses] = useState<ComplianceClause[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [mode, setMode] = useState<ComplianceMode>("problem");
  const [problemBrief, setProblemBrief] = useState("");
  const [standards, setStandards] = useState<StandardDocument[]>([]);
  const [stdQuery, setStdQuery] = useState("");
  const [selected, setSelected] = useState<StandardDocument[]>([]);
  const [authorities, setAuthorities] = useState<string[]>(["FAA", "EASA"]);
  const [model, setModel] = useState("gpt-4o-mini");
  const [extra, setExtra] = useState<string[]>(["", "", ""]);
  const [instructions, setInstructions] = useState("");
  const [run, setRun] = useState<ComplianceRun | null>(null);
  const [history, setHistory] = useState<ComplianceHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
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
    let alive = true;
    const timer = window.setTimeout(async () => {
      try {
        const data = await api<{ standards: StandardDocument[] }>(
          `/api/compliance/standards?q=${encodeURIComponent(libraryQuery)}`,
        );
        if (alive) setLibraryDocs(data.standards);
      } catch {
        /* non-critical */
      }
    }, 250);
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [libraryQuery]);

  async function loadHistory() {
    try {
      const data = await api<{ runs: ComplianceHistoryItem[] }>("/api/compliance/history");
      setHistory(data.runs);
    } catch {
      /* non-critical */
    }
  }

  useEffect(() => {
    void loadHistory();
  }, []);

  useEffect(() => {
    if (stage !== "running" || !runId) return;
    const timer = window.setInterval(async () => {
      try {
        const data = await api<ComplianceRun>(`/api/compliance/${runId}`);
        setRun(data);
        if (data.status === "done") {
          setStage("results");
          void loadHistory();
        } else if (data.status === "error" || data.status === "cancelled") {
          setStage("setup");
          setError(data.error || "The run was cancelled.");
          void loadHistory();
        }
      } catch {
        /* keep polling */
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [stage, runId]);

  function reset() {
    setStage("input");
    setFile(null);
    setLibraryDoc(null);
    setRunId(null);
    setFilename("");
    setClauses([]);
    setWarnings([]);
    setSelected([]);
    setRun(null);
    setError("");
    setInstructions("");
    setProblemBrief("");
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
      setLibraryDoc(null);
      setStage("setup");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function useLibraryDocument(doc: StandardDocument) {
    setBusy(true);
    setError("");
    try {
      const data = await libraryCompliance(doc.id);
      setRunId(data.run_id);
      setFilename(data.filename);
      setClauses(data.clauses);
      setWarnings(data.warnings);
      setLibraryDoc(doc);
      setSelected([]);
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

  function toggleAuthority(authority: string) {
    setAuthorities((prev) =>
      prev.includes(authority) ? prev.filter((a) => a !== authority) : [...prev, authority],
    );
  }

  async function startRun() {
    if (!runId) return;
    if (mode === "gap" && selected.length === 0) {
      setError("Select at least one standard for a gap review.");
      return;
    }
    if (clauses.length === 0) {
      setError("Add at least one clause.");
      return;
    }
    if (mode !== "gap" && !problemBrief.trim()) {
      setError("Describe the problem or improvement question you want analysed.");
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
          mode,
          problem_brief: problemBrief,
          authorities,
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

  async function openHistoryItem(item: ComplianceHistoryItem) {
    setError("");
    try {
      const data = await api<ComplianceRun>(`/api/compliance/${item.run_id}`);
      setRun(data);
      setRunId(data.run_id);
      setFilename(data.filename);
      setClauses(data.clauses);
      setMode(data.mode);
      setProblemBrief(data.problem_brief || "");
      setSelected([]);
      setStage(data.status === "done" ? "results" : data.status === "running" ? "running" : "setup");
    } catch (err) {
      setError(`${errorText(err)} The full text of a run expires after two hours; the history entry remains metadata only.`);
    }
  }

  async function deleteHistoryItem(item: ComplianceHistoryItem) {
    try {
      await api(`/api/compliance/history/${item.run_id}`, { method: "DELETE" });
      setHistory((prev) => prev.filter((x) => x.run_id !== item.run_id));
      if (runId === item.run_id) reset();
    } catch (err) {
      setError(errorText(err));
    }
  }

  const counts = (run?.results ?? []).reduce<Record<string, number>>((acc, r) => {
    acc[r.status] = (acc[r.status] ?? 0) + 1;
    return acc;
  }, {});
  const narrative = (run?.narrative && Object.keys(run.narrative).length > 0
    ? run.narrative
    : null) as ComplianceNarrative | null;
  const isProblem = mode !== "gap";
  const resultMode = run?.mode ?? mode;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-5 py-6">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-slate-800">Compliance workspace</h1>
            <p className="mt-1 max-w-3xl text-sm text-slate-500">
              Start from a problem or improvement question, or run a clause-level gap review.
              Uploads are transient; indexed library documents are used in place without creating a duplicate.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowHistory((v) => !v)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            {showHistory ? "Hide history" : `History (${history.length})`}
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {showHistory && (
          <section className="mb-5 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">Run history</h2>
                <p className="text-xs text-slate-400">Metadata only: file, date, mode, sources, model and status. No procedure text or answers.</p>
              </div>
              <button type="button" onClick={() => void loadHistory()} className="text-xs font-medium text-sky-700 hover:underline">
                Refresh
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {history.length === 0 && <p className="text-xs text-slate-400">No runs yet. Metadata is kept for 90 days.</p>}
              {history.map((item) => (
                <div key={item.run_id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2">
                  <button type="button" onClick={() => void openHistoryItem(item)} className="min-w-0 text-left">
                    <div className="truncate text-xs font-medium text-slate-700">{item.filename}</div>
                    <div className="mt-0.5 text-[11px] text-slate-400">
                      {formatDate(item.created_at)} · {modeLabel(item.mode)} · {item.model} · {item.status} · {item.standards.length || item.authorities.length || "all"} source(s)
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => void deleteHistoryItem(item)}
                    className="text-[11px] font-medium text-rose-600 hover:underline"
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {stage === "input" && (
          <div className="grid max-w-5xl gap-5 lg:grid-cols-2">
            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex gap-1 rounded-lg bg-slate-100 p-1">
                <button type="button" onClick={() => setInputKind("upload")} className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium ${inputKind === "upload" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500"}`}>
                  Upload PDF / DOCX
                </button>
                <button type="button" onClick={() => setInputKind("library")} className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium ${inputKind === "library" ? "bg-white text-slate-800 shadow-sm" : "text-slate-500"}`}>
                  Indexed library document
                </button>
              </div>

              {inputKind === "upload" ? (
                <form onSubmit={onUpload} className="mt-5">
                  <label className="block text-sm font-medium text-slate-700">
                    Procedure or document
                    <input
                      type="file"
                      accept=".pdf,.docx"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                      className="mt-2 block w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="mt-4 flex items-start gap-2 text-sm text-slate-600">
                    <input type="checkbox" checked={ocr} onChange={(e) => setOcr(e.target.checked)} className="mt-0.5" />
                    <span>OCR scanned pages (slower). Leave off for text PDFs and DOCX files.</span>
                  </label>
                  <button type="submit" disabled={!file || busy} className="mt-5 rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50">
                    {busy ? "Reading document…" : "Use this document"}
                  </button>
                </form>
              ) : (
                <div className="mt-5">
                  <p className="text-sm text-slate-600">Choose an already indexed procedure, report or standard from the library.</p>
                  <input
                    value={libraryQuery}
                    onChange={(e) => setLibraryQuery(e.target.value)}
                    placeholder="Search the indexed library…"
                    className="mt-3 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:bg-white"
                  />
                  <div className="mt-2 max-h-72 space-y-1 overflow-y-auto">
                    {libraryDocs.map((doc) => (
                      <button
                        type="button"
                        key={doc.id}
                        disabled={busy}
                        onClick={() => void useLibraryDocument(doc)}
                        className="flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left text-xs text-slate-600 transition hover:bg-sky-50 hover:text-sky-800 disabled:opacity-50"
                      >
                        <span className="mt-0.5 h-3 w-3 shrink-0 rounded border border-slate-300" />
                        <span className="min-w-0">
                          <span className="block truncate font-medium">{doc.title}</span>
                          <span className="text-[11px] text-slate-400">{doc.collection} · {doc.pages} pp · {doc.status}</span>
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-800">What do you want to do?</h2>
              <div className="mt-3 space-y-2">
                {([
                  ["problem", "Analyse a problem", "Describe an operational or quality problem. The analyst retrieves applicable FAA/EASA or other library evidence and proposes risk-based actions."],
                  ["improvement", "Improvement review", "Review a procedure for weaknesses and practical improvements, without forcing a compliance matrix."],
                  ["gap", "Gap / coverage review", "Compare each clause with one or more selected standards and produce a compliance matrix."],
                ] as [ComplianceMode, string, string][]).map(([value, title, description]) => (
                  <button
                    type="button"
                    key={value}
                    onClick={() => setMode(value)}
                    className={`block w-full rounded-lg border px-3 py-3 text-left ${mode === value ? "border-sky-300 bg-sky-50" : "border-slate-200 hover:bg-slate-50"}`}
                  >
                    <div className="text-sm font-medium text-slate-800">{title}</div>
                    <div className="mt-1 text-xs leading-5 text-slate-500">{description}</div>
                  </button>
                ))}
              </div>
              <p className="mt-4 text-[11px] text-slate-400">
                FAA and EASA are the primary sources. ICAO, AQAP, NASA and books are secondary evidence.
              </p>
            </section>
          </div>
        )}

        {stage === "setup" && (
          <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-800">Document evidence</h2>
                  <p className="text-xs text-slate-400">{filename} · {clauses.length} clause(s){libraryDoc ? ` · ${libraryDoc.collection}` : " · uploaded"}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setClauses((prev) => [...prev, { id: String(prev.length + 1), heading: "", text: "" }])}
                  className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  + Add clause
                </button>
              </div>
              {warnings.length > 0 && <div className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">{warnings.join(" ")}</div>}
              <div className="mt-4 max-h-[55vh] space-y-3 overflow-y-auto pr-1">
                {clauses.map((clause, idx) => (
                  <div key={`${clause.id}-${idx}`} className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-white px-1.5 py-0.5 text-[11px] font-semibold text-slate-500">{clause.id}</span>
                      <input
                        value={clause.heading}
                        onChange={(e) => setClauses((prev) => prev.map((c, i) => (i === idx ? { ...c, heading: e.target.value } : c)))}
                        placeholder="Clause heading"
                        className="min-w-0 flex-1 rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium"
                      />
                      <button type="button" aria-label="Remove clause" onClick={() => setClauses((prev) => prev.filter((_, i) => i !== idx))} className="rounded px-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600">×</button>
                    </div>
                    <textarea
                      value={clause.text}
                      onChange={(e) => setClauses((prev) => prev.map((c, i) => (i === idx ? { ...c, text: e.target.value } : c)))}
                      rows={3}
                      className="mt-2 w-full resize-y rounded border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700"
                    />
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-4">
              {isProblem && (
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h2 className="text-sm font-semibold text-slate-800">Problem or improvement brief</h2>
                  <p className="mt-1 text-xs text-slate-400">What happened, what decision do you need, and what would “good” look like?</p>
                  <textarea
                    value={problemBrief}
                    onChange={(e) => setProblemBrief(e.target.value)}
                    rows={5}
                    placeholder="Example: During an assembly-line audit, torque records were missing for a batch of parts. Analyse the procedure, applicable FAA/EASA requirements and SMS expectations; identify contributing factors, risk and corrective actions."
                    className="mt-3 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:bg-white"
                  />
                </div>
              )}

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-800">{isProblem ? "Source scope" : "Standard(s) for this request"}</h2>
                <p className="mt-1 text-xs text-slate-400">
                  {isProblem
                    ? "Pick specific documents, or leave them unselected and use the authority filter. FAA/EASA are primary."
                    : "Search and select the standards you named, e.g. AS9100D, ISO 9001, 14 CFR Part 5."}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {AUTHORITIES.map((authority) => (
                    <button
                      type="button"
                      key={authority}
                      onClick={() => toggleAuthority(authority)}
                      className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${authorities.includes(authority) ? "border-sky-300 bg-sky-50 text-sky-800" : "border-slate-200 text-slate-500 hover:bg-slate-50"}`}
                    >
                      {authority}
                    </button>
                  ))}
                </div>
                <input
                  value={stdQuery}
                  onChange={(e) => setStdQuery(e.target.value)}
                  placeholder="Search documents…"
                  className="mt-3 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-sky-500 focus:bg-white"
                />
                <div className="mt-2 max-h-48 space-y-1 overflow-y-auto">
                  {standards.map((doc) => {
                    const active = selected.some((s) => s.id === doc.id);
                    return (
                      <button
                        type="button"
                        key={doc.id}
                        onClick={() => toggleStandard(doc)}
                        className={`flex w-full items-start gap-2 rounded-lg px-2.5 py-2 text-left text-xs transition ${active ? "bg-sky-50 text-sky-800" : "hover:bg-slate-50 text-slate-600"}`}
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
                      <button type="button" key={s.id} onClick={() => toggleStandard(s)} className="rounded-full bg-sky-100 px-2.5 py-1 text-[11px] font-medium text-sky-800" title="Remove">
                        {s.title.slice(0, 45)} ×
                      </button>
                    ))}
                  </div>
                )}
                {isProblem && selected.length === 0 && (
                  <p className="mt-2 text-[11px] text-slate-400">
                    {authorities.length ? `Searching ${authorities.join(", ")}.` : "Searching the whole indexed library."}
                  </p>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-800">Analysis options</h2>
                <label className="mt-3 block text-xs font-medium text-slate-500">
                  Model
                  <select value={model} onChange={(e) => setModel(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-sm">
                    <option value="gpt-4o-mini">gpt-4o-mini · fast</option>
                    <option value="gpt-4o">gpt-4o · deeper</option>
                  </select>
                </label>
                {mode === "gap" && (
                  <div className="mt-3">
                    <div className="text-xs font-medium text-slate-500">Extra columns (optional, max 3)</div>
                    {extra.map((value, i) => (
                      <input key={i} value={value} onChange={(e) => setExtra((prev) => prev.map((x, j) => (j === i ? e.target.value : x)))} placeholder={["e.g. Risk rating", "e.g. Action owner", "e.g. Due date"][i]} className="mt-1.5 w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs" />
                    ))}
                  </div>
                )}
                <label className="mt-3 block text-xs font-medium text-slate-500">
                  Additional instructions (optional)
                  <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={3} placeholder="e.g. Focus on training records, shift handover and verification evidence." className="mt-1 w-full resize-y rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs" />
                </label>
                <button type="button" onClick={() => void startRun()} disabled={busy || (mode === "gap" && selected.length === 0)} className="mt-4 w-full rounded-lg bg-sky-700 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50">
                  {busy ? "Starting…" : modeLabel(mode)}
                </button>
                <button type="button" onClick={reset} className="mt-2 w-full text-xs text-slate-400 hover:text-slate-600">Start over</button>
              </div>
            </section>
          </div>
        )}

        {stage === "running" && run && (
          <div className="max-w-3xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-800">{modeLabel(run.mode)}…</h2>
                <p className="text-xs text-slate-400">{run.mode === "gap" ? `${run.progress} of ${run.total}` : "Retrieving evidence and composing the analysis"} · {run.model}</p>
              </div>
              <button type="button" onClick={() => void cancelRun()} className="rounded-md border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50">Cancel</button>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-sky-600 transition-all" style={{ width: `${run.total ? (run.progress / run.total) * 100 : 35}%` }} />
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
                <h2 className="text-sm font-semibold text-slate-800">{filename} · {modeLabel(resultMode)}</h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  {resultMode === "gap"
                    ? `${run.results.length} clause(s) · ${Object.entries(counts).map(([k, v]) => `${k}: ${v}`).join(" · ")}`
                    : `${narrative?.applicable_requirements.length ?? 0} requirement(s) · ${narrative?.gaps_or_conflicts.length ?? 0} finding(s) · risk ${narrative?.risk_assessment.risk_level ?? "Unclear"}`}
                </p>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => void downloadCompliance(run.run_id, "xlsx", filename.replace(/\.[^.]+$/, ""), resultMode === "gap" ? "compliance" : "analysis")} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50">Export XLSX</button>
                <button type="button" onClick={() => void downloadCompliance(run.run_id, "docx", filename.replace(/\.[^.]+$/, ""), resultMode === "gap" ? "compliance" : "analysis")} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50">Export DOCX</button>
                <button type="button" onClick={reset} className="rounded-lg bg-sky-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-800">New analysis</button>
              </div>
            </div>

            {resultMode !== "gap" && narrative && (
              <div className="space-y-4">
                <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-800">Problem understanding</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{narrative.problem_understanding || "—"}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className={`rounded-full border px-2.5 py-1 font-medium ${SEVERITY_STYLE[narrative.risk_assessment.risk_level] ?? STATUS_STYLE.Unclear}`}>Risk: {narrative.risk_assessment.risk_level || "Unclear"}</span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-slate-500">Likelihood: {narrative.risk_assessment.likelihood || "Unclear"}</span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-slate-500">Severity: {narrative.risk_assessment.severity || "Unclear"}</span>
                  </div>
                  {narrative.risk_assessment.rationale && <p className="mt-2 text-xs italic text-slate-500">{narrative.risk_assessment.rationale}</p>}
                </section>

                {narrative.applicable_requirements.length > 0 && (
                  <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
                    <div className="border-b border-slate-100 px-4 py-3"><h3 className="text-sm font-semibold text-slate-800">Applicable requirements</h3></div>
                    <table className="min-w-[900px] w-full text-left text-xs">
                      <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-400"><tr><th className="px-3 py-2">Requirement</th><th className="px-3 py-2">Source / page</th><th className="px-3 py-2">Evidence</th><th className="px-3 py-2">Relevance</th></tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {narrative.applicable_requirements.map((r, i) => (
                          <tr key={i} className="align-top hover:bg-slate-50/60">
                            <td className="max-w-[300px] px-3 py-2 text-slate-700">{r.requirement}</td>
                            <td className="max-w-[220px] px-3 py-2 text-slate-600">
                              <div className="truncate">{r.document || "—"}</div>
                              <div className="text-[11px] text-slate-400">{r.authority} {r.clause ? `· ${r.clause}` : ""}</div>
                              {r.document && r.document_id ? <button type="button" onClick={() => onOpenSource({ documentId: r.document_id as number, title: r.document, page: r.page, excerpt: r.evidence })} className="mt-1 text-[11px] font-medium text-sky-700 hover:underline">Open p.{r.page}</button> : r.document ? <div className="mt-1 text-[11px] text-slate-400">Cited p.{r.page}</div> : null}
                            </td>
                            <td className="max-w-[280px] px-3 py-2 italic text-slate-500">{r.evidence || "—"}</td>
                            <td className="max-w-[220px] px-3 py-2 text-slate-600">{r.relevance || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </section>
                )}

                <div className="grid gap-4 lg:grid-cols-2">
                  <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-slate-800">Gaps, conflicts and contributing factors</h3>
                    <div className="mt-3 space-y-3">
                      {narrative.gaps_or_conflicts.length === 0 && <p className="text-xs text-slate-400">No specific gap was identified from the available evidence.</p>}
                      {narrative.gaps_or_conflicts.map((g, i) => (
                        <div key={i} className="rounded-lg border border-slate-100 bg-slate-50/60 p-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="text-xs font-medium text-slate-700">{g.issue}</div>
                            <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${SEVERITY_STYLE[g.severity] ?? STATUS_STYLE.Unclear}`}>{g.severity || "Unclear"}</span>
                          </div>
                          <p className="mt-1 text-xs text-slate-500">{g.why_it_matters}</p>
                          {g.evidence && <p className="mt-1 text-[11px] italic text-slate-400">{g.evidence}</p>}
                        </div>
                      ))}
                      {narrative.contributing_factors.map((f, i) => (
                        <div key={`factor-${i}`} className="rounded-lg border border-slate-100 p-3">
                          <div className="text-xs font-medium text-slate-700">{f.factor} <span className="font-normal text-slate-400">· {f.confidence}</span></div>
                          <p className="mt-1 text-xs text-slate-500">{f.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </section>

                  <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-slate-800">Corrective actions and verification</h3>
                    <div className="mt-3 space-y-3">
                      {narrative.corrective_actions.length === 0 && <p className="text-xs text-slate-400">No corrective action was generated. Review the limitations.</p>}
                      {narrative.corrective_actions.map((a, i) => (
                        <div key={i} className="rounded-lg border border-slate-100 p-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="text-xs font-medium text-slate-700">{a.action}</div>
                            <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium ${SEVERITY_STYLE[a.priority] ?? STATUS_STYLE.Unclear}`}>{a.priority || "—"}</span>
                          </div>
                          <div className="mt-1 text-[11px] text-slate-400">{a.owner || "Owner to assign"} · {a.verification || "Verification to define"}</div>
                        </div>
                      ))}
                    </div>
                    {narrative.verification && <p className="mt-3 text-xs text-slate-500"><span className="font-medium text-slate-700">Verification:</span> {narrative.verification}</p>}
                    {narrative.limitations && <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700"><span className="font-medium">Limitations:</span> {narrative.limitations}</p>}
                  </section>
                </div>

                {narrative.citations.length > 0 && (
                  <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <h3 className="text-sm font-semibold text-slate-800">Page citations</h3>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      {narrative.citations.map((c) => (
                        <button key={c.ref} type="button" onClick={() => onOpenSource({ documentId: c.document_id, title: c.document, page: c.page })} className="rounded-lg border border-slate-100 px-3 py-2 text-left text-xs text-slate-600 hover:bg-slate-50">
                          <span className="font-medium text-sky-700">[{c.ref}]</span> {c.document} <span className="text-slate-400">· p.{c.page} · {c.collection}</span>
                        </button>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            )}

            {resultMode === "gap" && (
              <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
                <table className="min-w-[900px] w-full text-left text-xs">
                  <thead className="bg-slate-50 text-[11px] uppercase tracking-wide text-slate-400">
                    <tr><th className="px-3 py-2">Clause</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">Requirement</th><th className="px-3 py-2">Standard / page</th><th className="px-3 py-2">Action</th>{run.extra_columns.map((c) => <th key={c} className="px-3 py-2">{c}</th>)}</tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {run.results.map((r: ComplianceResult) => (
                      <tr key={r.clause_id} className="align-top hover:bg-slate-50/60">
                        <td className="max-w-[220px] px-3 py-2"><div className="font-medium text-slate-700">{r.clause_heading || `Clause ${r.clause_id}`}</div><div className="mt-0.5 line-clamp-2 text-[11px] text-slate-400">{r.clause_excerpt}</div></td>
                        <td className="px-3 py-2"><span className={`inline-block rounded-full border px-2 py-0.5 font-medium ${STATUS_STYLE[r.status]}`}>{r.status}</span><div className="mt-1 text-[10px] text-slate-400">{r.confidence} confidence</div></td>
                        <td className="max-w-[260px] px-3 py-2 text-slate-600"><div>{r.requirement}</div><div className="mt-1 text-[11px] italic text-slate-400">{r.rationale}</div></td>
                        <td className="max-w-[180px] px-3 py-2 text-slate-600"><div className="truncate">{r.standard || "—"}</div>{r.document_id > 0 && <button type="button" onClick={() => onOpenSource({ documentId: r.document_id, title: r.standard, page: r.page, excerpt: r.evidence })} className="mt-1 text-[11px] font-medium text-sky-700 hover:underline">Open p.{r.page}</button>}</td>
                        <td className="max-w-[240px] px-3 py-2 text-slate-600">{r.action || "—"}</td>
                        {run.extra_columns.map((c) => <td key={c} className="px-3 py-2 text-slate-500">{r.extras?.[c] || ""}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-[11px] text-slate-400">Decision-support output. Verify every finding against the cited source page before use. Run text expires after two hours; history keeps metadata only.</p>
          </div>
        )}
      </div>
    </div>
  );
}
