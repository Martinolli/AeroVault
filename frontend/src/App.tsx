import { useEffect, useState } from "react";
import { api, formatDate } from "./lib/api";
import type { ChatSummary, ViewerTarget } from "./types";
import { Brand, LoginScreen, SetupScreen } from "./components/Auth";
import ChatView from "./components/ChatView";
import ComplianceView from "./components/ComplianceView";
import Library from "./components/Library";
import PdfViewer from "./components/PdfViewer";

type AuthState = "loading" | "setup" | "login" | "ready";
type View = "chat" | "library" | "compliance";

export default function App() {
  const [auth, setAuth] = useState<AuthState>("loading");
  const [view, setView] = useState<View>("chat");
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [historyQuery, setHistoryQuery] = useState("");
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [chatKey, setChatKey] = useState(0);
  const [viewer, setViewer] = useState<ViewerTarget | null>(null);
  const [mobileNav, setMobileNav] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const status = await api<{ configured: boolean }>("/api/auth/status");
        if (!status.configured) {
          setAuth("setup");
          return;
        }
        const me = await api<{ authenticated: boolean }>("/api/auth/me");
        setAuth(me.authenticated ? "ready" : "login");
      } catch {
        setAuth("login");
      }
    })();
  }, []);

  async function loadChats(query: string) {
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      const data = await api<{ chats: ChatSummary[] }>(`/api/chats?${params.toString()}`);
      setChats(data.chats);
    } catch {
      /* history is non-critical */
    }
  }

  useEffect(() => {
    if (auth !== "ready") return;
    const timer = window.setTimeout(() => void loadChats(historyQuery), 250);
    return () => window.clearTimeout(timer);
  }, [auth, historyQuery]);

  function newChat() {
    setActiveChatId(null);
    setView("chat");
    setChatKey((k) => k + 1);
    setMobileNav(false);
  }

  function selectChat(id: number) {
    setActiveChatId(id);
    setView("chat");
    setChatKey((k) => k + 1);
    setMobileNav(false);
  }

  async function deleteChat(id: number, event: React.MouseEvent) {
    event.stopPropagation();
    if (!window.confirm("Delete this conversation? This cannot be undone.")) return;
    try {
      await api(`/api/chats/${id}`, { method: "DELETE" });
      if (activeChatId === id) newChat();
      await loadChats(historyQuery);
    } catch {
      /* ignore */
    }
  }

  async function logout() {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } finally {
      setAuth("login");
      setChats([]);
      setActiveChatId(null);
    }
  }

  if (auth === "loading") {
    return (
      <div className="chart-bg flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading AeroVault…
      </div>
    );
  }
  if (auth === "setup") return <SetupScreen onDone={() => setAuth("ready")} />;
  if (auth === "login") return <LoginScreen onDone={() => setAuth("ready")} />;

  return (
    <div className="chart-bg flex h-screen overflow-hidden">
      <aside
        className={`${
          mobileNav ? "flex" : "hidden"
        } absolute inset-y-0 left-0 z-40 w-72 flex-col border-r border-slate-200 bg-white/95 backdrop-blur md:relative md:flex`}
      >
        <div className="border-b border-slate-100 px-5 py-4">
          <Brand subtitle="Decision support" />
        </div>

        <div className="space-y-2 px-3 pt-3">
          <button
            type="button"
            onClick={newChat}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-sky-700 px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800"
          >
            <span className="text-base leading-none">+</span> New question
          </button>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <button
              type="button"
              onClick={() => {
                setView("chat");
                setMobileNav(false);
              }}
              className={`rounded-lg px-3 py-2 font-medium transition ${
                view === "chat" ? "bg-sky-50 text-sky-800" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              Chat
            </button>
            <button
              type="button"
              onClick={() => {
                setView("library");
                setMobileNav(false);
              }}
              className={`rounded-lg px-3 py-2 font-medium transition ${
                view === "library" ? "bg-sky-50 text-sky-800" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              Library
            </button>
            <button
              type="button"
              onClick={() => {
                setView("compliance");
                setMobileNav(false);
              }}
              className={`rounded-lg px-3 py-2 font-medium transition ${
                view === "compliance" ? "bg-sky-50 text-sky-800" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              Compliance
            </button>
          </div>
        </div>

        <div className="mt-4 flex min-h-0 flex-1 flex-col px-3">
          <div className="mb-1 px-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">History</div>
          <input
            value={historyQuery}
            onChange={(e) => setHistoryQuery(e.target.value)}
            placeholder="Search conversations…"
            className="mb-2 w-full rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-700 outline-none focus:border-sky-500 focus:bg-white"
          />
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pb-3">
            {chats.map((chat) => (
              <div
                key={chat.id}
                role="button"
                tabIndex={0}
                onClick={() => selectChat(chat.id)}
                onKeyDown={(e) => e.key === "Enter" && selectChat(chat.id)}
                className={`group flex cursor-pointer items-start gap-2 rounded-lg px-2.5 py-2 text-left transition ${
                  activeChatId === chat.id ? "bg-sky-50" : "hover:bg-slate-50"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate text-xs font-medium text-slate-700">{chat.title}</div>
                  <div className="mt-0.5 text-[11px] text-slate-400">
                    {formatDate(chat.updated_at)} · {chat.messages} msg
                  </div>
                </div>
                <button
                  type="button"
                  aria-label="Delete conversation"
                  onClick={(e) => void deleteChat(chat.id, e)}
                  className="mt-0.5 hidden rounded px-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 group-hover:block"
                >
                  ×
                </button>
              </div>
            ))}
            {chats.length === 0 && (
              <div className="px-1 py-2 text-xs text-slate-400">No conversations yet.</div>
            )}
          </div>
        </div>

        <div className="border-t border-slate-100 px-4 py-3">
          <div className="mb-2 flex items-center gap-1.5 text-[11px] text-slate-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Local · 127.0.0.1 only
          </div>
          <button
            type="button"
            onClick={() => void logout()}
            className="w-full rounded-md border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            Sign out
          </button>
        </div>
      </aside>

      {mobileNav && (
        <div className="fixed inset-0 z-30 bg-slate-900/30 md:hidden" onClick={() => setMobileNav(false)} />
      )}

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2 md:hidden">
          <button
            type="button"
            onClick={() => setMobileNav((v) => !v)}
            className="rounded border border-slate-300 px-2 py-1 text-sm text-slate-700"
          >
            ☰
          </button>
          <span className="text-sm font-semibold text-slate-800">AeroVault</span>
        </div>
        {view === "chat" ? (
          <ChatView
            key={chatKey}
            chatId={activeChatId}
            onChatCreated={(id) => setActiveChatId(id)}
            onHistoryChange={() => void loadChats(historyQuery)}
            onOpenSource={setViewer}
          />
        ) : view === "library" ? (
          <Library onOpenDocument={setViewer} />
        ) : (
          <ComplianceView onOpenSource={setViewer} />
        )}
      </main>

      {viewer && <PdfViewer target={viewer} onClose={() => setViewer(null)} />}
    </div>
  );
}
