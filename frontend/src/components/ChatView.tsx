import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, streamChat } from "../lib/api";
import type { ChatDetail, ChatMessage, Source, ViewerTarget } from "../types";

const MODELS = [
  { id: "gpt-4o-mini", label: "gpt-4o-mini · fast" },
  { id: "gpt-4o", label: "gpt-4o · deeper" },
];

const SUGGESTIONS = [
  "How should a safety risk assessment be structured under an SMS?",
  "What are the key principles of Reason's model of organisational accidents?",
  "What does DO-178C require for software verification objectives?",
  "How does Maintenance Resource Management reduce maintenance errors?",
];

type Props = {
  chatId: number | null;
  onChatCreated: (id: number) => void;
  onHistoryChange: () => void;
  onOpenSource: (target: ViewerTarget) => void;
};

function CitationMarkdown({
  content,
  sources,
  onOpenSource,
}: {
  content: string;
  sources: Source[];
  onOpenSource: (target: ViewerTarget) => void;
}) {
  const prepared = content.replace(/\[S(\d+)\]/g, (_match, n: string) => `[S${n}](#cite-S${n})`);
  const byTag = useMemo(() => new Map(sources.map((s) => [s.tag, s])), [sources]);

  return (
    <div className="prose-av">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
            if (href?.startsWith("#cite-")) {
              const tag = href.slice(6);
              const source = byTag.get(tag);
              return (
                <button
                  type="button"
                  title={source ? `${source.title} — p. ${source.page}` : tag}
                  onClick={() =>
                    source &&
                    onOpenSource({
                      documentId: source.document_id,
                      title: source.title,
                      page: source.page,
                      excerpt: source.excerpt,
                    })
                  }
                  className="cite-chip"
                >
                  {tag}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {prepared}
      </ReactMarkdown>
    </div>
  );
}

function SourceList({
  sources,
  onOpenSource,
}: {
  sources: Source[];
  onOpenSource: (target: ViewerTarget) => void;
}) {
  if (!sources.length) return null;
  return (
    <div className="mt-3 border-t border-slate-200 pt-2">
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Sources</div>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((s) => (
          <button
            key={s.tag}
            type="button"
            onClick={() =>
              onOpenSource({
                documentId: s.document_id,
                title: s.title,
                page: s.page,
                excerpt: s.excerpt,
              })
            }
            className="group flex max-w-full items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-left text-xs text-slate-600 transition hover:border-sky-300 hover:bg-sky-50"
          >
            <span className="rounded bg-sky-100 px-1 py-0.5 font-mono text-[10px] font-semibold text-sky-800">
              {s.tag}
            </span>
            <span className="truncate max-w-[22rem] group-hover:text-sky-800">{s.title}</span>
            <span className="whitespace-nowrap text-slate-400">p. {s.page}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatView({ chatId, onChatCreated, onHistoryChange, onOpenSource }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const createdRef = useRef<number | null>(null);

  useEffect(() => {
    setError(null);
    if (chatId === null) {
      setMessages([]);
      setModel("gpt-4o-mini");
      return;
    }
    if (createdRef.current === chatId) return;
    let cancelled = false;
    setLoading(true);
    api<ChatDetail>(`/api/chats/${chatId}`)
      .then((chat) => {
        if (cancelled) return;
        setMessages(chat.messages);
        setModel(chat.model);
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  async function send(questionOverride?: string) {
    const question = (questionOverride ?? input).trim();
    if (!question || busy) return;
    setInput("");
    setError(null);
    setBusy(true);
    const userMessage: ChatMessage = { role: "user", content: question };
    const placeholder: ChatMessage = { role: "assistant", content: "", sources: [] };
    setMessages((prev) => [...prev, userMessage, placeholder]);

    const controller = new AbortController();
    abortRef.current = controller;

    const updateAssistant = (patch: (msg: ChatMessage) => ChatMessage) => {
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i -= 1) {
          if (next[i].role === "assistant") {
            next[i] = patch(next[i]);
            break;
          }
        }
        return next;
      });
    };

    try {
      await streamChat(
        { question, chat_id: chatId, model },
        {
          onSources: (sources) => updateAssistant((m) => ({ ...m, sources })),
          onDelta: (delta) => updateAssistant((m) => ({ ...m, content: m.content + delta })),
          onDone: (payload) => {
            if (chatId === null) {
              createdRef.current = payload.chat_id;
              onChatCreated(payload.chat_id);
            }
            onHistoryChange();
          },
          onError: (detail) => setError(detail),
        },
        controller.signal,
      );
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError(err instanceof Error ? err.message : String(err));
      }
      onHistoryChange();
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  function stop() {
    abortRef.current?.abort();
    setBusy(false);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white/80 px-6 py-3 backdrop-blur">
        <div>
          <h1 className="text-sm font-semibold text-slate-800">Ask the library</h1>
          <p className="text-xs text-slate-500">Answers cite book and page — click a citation to open the PDF.</p>
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-500">
          Model
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={busy}
            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 outline-none focus:border-sky-500"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mx-auto max-w-3xl space-y-5">
          {loading && <div className="text-sm text-slate-400">Loading conversation…</div>}
          {!loading && messages.length === 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">What do you need to decide?</h2>
              <p className="mt-1 text-sm text-slate-500">
                Ask about safety risk management, human factors, certification or quality standards. AeroVault searches
                your indexed collection and answers with page-level citations.
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => void send(s)}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm text-slate-600 transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-900"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, index) =>
            message.role === "user" ? (
              <div key={index} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-sky-700 px-4 py-2.5 text-sm text-white shadow-sm">
                  {message.content}
                </div>
              </div>
            ) : (
              <div key={index} className="flex justify-start">
                <div className="w-full max-w-[95%] rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 shadow-sm">
                  {message.content ? (
                    <CitationMarkdown
                      content={message.content}
                      sources={message.sources ?? []}
                      onOpenSource={onOpenSource}
                    />
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-sky-500" />
                      Searching the library and drafting an answer…
                    </div>
                  )}
                  <SourceList sources={message.sources ?? []} onOpenSource={onOpenSource} />
                </div>
              </div>
            ),
          )}
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-4 py-3 sm:px-8">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end gap-2 rounded-xl border border-slate-300 bg-white p-2 shadow-sm focus-within:border-sky-500 focus-within:ring-2 focus-within:ring-sky-500/20">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
              placeholder="Ask about your documents… (Enter to send, Shift+Enter for a new line)"
              className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1 text-sm text-slate-800 outline-none placeholder:text-slate-400"
            />
            {busy ? (
              <button
                type="button"
                onClick={stop}
                className="rounded-lg bg-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-300"
              >
                Stop
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void send()}
                disabled={!input.trim()}
                className="rounded-lg bg-sky-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-sky-800 disabled:opacity-40"
              >
                Send
              </button>
            )}
          </div>
          <p className="mt-1.5 text-center text-[11px] text-slate-400">
            Answers are grounded in indexed documents; verify critical decisions against the cited page.
          </p>
        </div>
      </div>
    </div>
  );
}
