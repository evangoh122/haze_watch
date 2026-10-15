import { FormEvent, useState } from "react";
import { postChat, type ChatMessage, type ChatResponse } from "../../lib/chat";

interface Turn {
  role: "user" | "assistant";
  content: string;
  meta?: ChatResponse;
}

/**
 * Grounded analyst chat panel. Every reply is built from the pipeline's own
 * datasets and comes back with provenance sources and the research disclaimer.
 */
export default function ChatPanel() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (!text || busy) return;

    const history: ChatMessage[] = [...turns.map((t) => ({ role: t.role, content: t.content })), { role: "user", content: text }];
    setTurns((prev) => [...prev, { role: "user", content: text }]);
    setQuestion("");
    setBusy(true);
    setError(null);
    try {
      const response = await postChat(history.slice(-20));
      setTurns((prev) => [...prev, { role: "assistant", content: response.reply, meta: response }]);
    } catch {
      setError("Chat request failed. Is the backend running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-surface-elevated">
      <div className="border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-primary">Ask the data</h2>
        <p className="text-xs text-muted">
          Answers are grounded in the registered pipeline datasets. Commercial data is synthetic.
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {turns.length === 0 && (
          <p className="text-sm text-muted">
            Try: &quot;What datasets are loaded?&quot; or &quot;How many concessions have fire
            detections?&quot;
          </p>
        )}
        {turns.map((turn, index) => (
          <div key={index} className={turn.role === "user" ? "text-right" : ""}>
            <div
              className={
                turn.role === "user"
                  ? "inline-block rounded-lg bg-blue-50 px-3 py-2 text-left text-sm text-blue-900"
                  : "rounded-lg bg-slate-50 px-3 py-2 text-sm text-primary"
              }
            >
              {turn.content}
            </div>
            {turn.meta && (
              <div className="mt-1 space-y-1 text-xs text-muted">
                {turn.meta.fallback && (
                  <span className="mr-2 rounded bg-amber-50 px-1.5 py-0.5 text-amber-700">
                    deterministic fallback - no LLM connected
                  </span>
                )}
                {turn.meta.guardrail_flags.length > 0 && (
                  <div className="rounded bg-rose-50 px-2 py-1 text-rose-700">
                    Guardrail flags: {turn.meta.guardrail_flags.join(", ")}
                  </div>
                )}
                {turn.meta.sources.length > 0 && (
                  <div>
                    Sources:{" "}
                    {turn.meta.sources.map((s, i) => (
                      <span key={i} className="mr-1 rounded bg-slate-100 px-1.5 py-0.5">
                        {s.dataset_id} ({s.treatment})
                      </span>
                    ))}
                  </div>
                )}
                <div className="text-[10px] text-muted">{turn.meta.disclaimer}</div>
              </div>
            )}
          </div>
        ))}
        {busy && <p className="text-xs text-muted">Thinking…</p>}
        {error && <p className="text-xs text-rose-600">{error}</p>}
      </div>

      <form onSubmit={submit} className="flex gap-2 border-t border-slate-100 p-3">
        <input
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          placeholder="Ask about exposure, datasets, or the data policy…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          aria-label="Chat question"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="rounded-md bg-blue-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
