import { useEffect, useRef, useState } from "react";
import api, { errorMessage } from "../api";
import Markdown from "../components/Markdown";
import { Page, buttonClass, inputClass, useAiStatus } from "../components/ui";

const SUGGESTIONS = [
  "Which items will run out of stock soonest?",
  "Summarize income and expenses for the last 30 days.",
  "Are there any unusual transactions?",
  "Which projects are at risk of missing their deadline?",
  "How many deliveries are still open, and which are oldest?",
];

const TOOL_LABEL = (name) => name.replaceAll("_", " ");

export default function Assistant() {
  const status = useAiStatus();
  const [messages, setMessages] = useState([]); // {role, content, tools?}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const ready = status?.reachable && status?.model_available;

  const send = async (text) => {
    const question = text.trim();
    if (!question || busy) return;
    const history = [...messages, { role: "user", content: question }];
    setMessages(history);
    setInput("");
    setBusy(true);
    setError("");
    try {
      const res = await api.post("/ai/chat", {
        messages: history.map(({ role, content }) => ({ role, content })),
      });
      setMessages([...history, { role: "assistant", content: res.data.reply || "(no answer)", tools: res.data.tools_used }]);
    } catch (err) {
      setError(errorMessage(err, "The assistant is unavailable."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page
      title="AI Assistant"
      subtitle={
        status === null ? "Checking AI service…"
          : ready ? `Answers come from your live data via a local model (${status.model}). It can read, not change, anything.`
            : status?.enabled === false ? "AI features are disabled on this server."
              : `The AI model is not available (${status?.model}). See the README section "AI setup".`
      }
      actions={messages.length > 0 && <button className={buttonClass.secondary} onClick={() => setMessages([])}>New chat</button>}
    >
      <div className="max-w-3xl">
        <div className="space-y-4 mb-6">
          {messages.length === 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
              <p className="text-gray-300 mb-4">Ask about stock, money, deliveries, people or projects. Try:</p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className={buttonClass.small} disabled={!ready} onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
              <div className={`rounded-2xl px-5 py-3 max-w-[90%] ${
                m.role === "user" ? "bg-indigo-600/80 text-white" : "bg-gray-900 border border-gray-800"
              }`}>
                {m.role === "user" ? <p className="text-sm whitespace-pre-wrap">{m.content}</p> : <Markdown text={m.content} />}
                {m.tools?.length > 0 && (
                  <p className="text-xs text-gray-500 mt-2">Looked at: {m.tools.map(TOOL_LABEL).join(", ")}</p>
                )}
              </div>
            </div>
          ))}

          {busy && <div className="text-sm text-gray-400 animate-pulse">Thinking… (local models can take a little while)</div>}
          {error && <div role="alert" className="text-sm text-red-300">{error}</div>}
          <div ref={bottom} />
        </div>

        <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-3 sticky bottom-4">
          <input className={`${inputClass} flex-1 py-3`} placeholder={ready ? "Ask a question…" : "AI unavailable"}
            value={input} maxLength={2000} disabled={!ready} onChange={(e) => setInput(e.target.value)} aria-label="Message" />
          <button className={buttonClass.primary} disabled={!ready || busy || !input.trim()}>Send</button>
        </form>
      </div>
    </Page>
  );
}
