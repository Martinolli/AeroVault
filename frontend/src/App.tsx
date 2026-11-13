import { useEffect, useState } from "react";

type Health = { status: string; app: string; version: string; env: string };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
      <div className="max-w-xl w-full rounded-xl border border-slate-800 bg-slate-900 p-8 shadow-xl">
        <h1 className="text-2xl font-semibold tracking-tight">AeroVault</h1>
        <p className="mt-2 text-sm text-slate-400">
          Local aviation library — decision support
        </p>
        <div className="mt-6 rounded-lg bg-slate-950 p-4 text-sm font-mono text-emerald-400">
          {health
            ? `API ok · v${health.version} · ${health.env}`
            : error
              ? `API unreachable: ${error}`
              : "Checking API…"}
        </div>
        <p className="mt-6 text-xs text-slate-500">
          Phase 1 scaffold — login, library and chat arrive in Phase 2.
        </p>
      </div>
    </main>
  );
}
