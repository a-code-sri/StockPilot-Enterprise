import { useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import Sidebar from "./Sidebar";
import Markdown from "./Markdown";

export function Page({ title, subtitle, actions, children }) {
  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />
      <main className="flex-1 min-w-0 p-8 lg:p-10">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl lg:text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
              {title}
            </h1>
            {subtitle && <p className="text-sm text-gray-400 mt-2">{subtitle}</p>}
          </div>
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
        {children}
      </main>
    </div>
  );
}

export function ErrorBanner({ message, onClose }) {
  if (!message) return null;
  return (
    <div role="alert" className="flex items-start justify-between gap-4 bg-red-900/40 border border-red-700 text-red-200 p-4 rounded-lg mb-6">
      <span>{message}</span>
      {onClose && (
        <button type="button" onClick={onClose} className="text-red-300 hover:text-white" aria-label="Dismiss">
          ✕
        </button>
      )}
    </div>
  );
}

export function Panel({ title, subtitle, action, children, className = "" }) {
  return (
    <section className={`bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden ${className}`}>
      {(title || action) && (
        <div className="p-5 border-b border-gray-800 flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold">{title}</h2>
            {subtitle && <div className="text-xs text-gray-400 mt-1">{subtitle}</div>}
          </div>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export const buttonClass = {
  primary: "bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-4 py-2 rounded-lg text-sm font-medium",
  secondary: "border border-gray-700 hover:border-indigo-500/50 disabled:opacity-50 px-4 py-2 rounded-lg text-sm",
  danger: "bg-red-600/80 hover:bg-red-600 disabled:opacity-50 px-3 py-1.5 rounded-lg text-sm",
  small: "border border-gray-700 hover:border-indigo-500/50 disabled:opacity-50 px-3 py-1.5 rounded-lg text-sm",
};

export const inputClass =
  "bg-gray-800 border border-gray-700 focus:border-indigo-500 focus:outline-none px-3 py-2 rounded-lg text-sm";

let aiStatusPromise = null;

/** Cached AI availability check, shared by every insights panel on the page. */
export function useAiStatus() {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    aiStatusPromise ||= api.get("/ai/status").then((r) => r.data).catch(() => null);
    let alive = true;
    aiStatusPromise.then((s) => alive && setStatus(s));
    return () => {
      alive = false;
    };
  }, []);
  return status;
}

/** "Summarize with AI" panel shown on analytics pages. */
export function InsightsPanel({ module }) {
  const { can } = useAuth();
  const status = useAiStatus();
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!can("ai.use")) return null;

  const ready = status?.reachable && status?.model_available;

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.post("/ai/insights", { module });
      setSummary(res.data.summary);
    } catch (e) {
      setError(errorMessage(e, "AI insights are unavailable."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      className="mb-8"
      title="AI insights"
      subtitle={
        status === null
          ? "Checking AI service…"
          : ready
            ? `Generated locally by ${status.model}. Based only on your data.`
            : status?.enabled === false
              ? "AI features are disabled on this server."
              : `AI model not available (${status?.model || "Ollama"}). See README → AI setup.`
      }
      action={
        <button type="button" className={buttonClass.primary} onClick={run} disabled={busy || !ready}>
          {busy ? "Thinking…" : summary ? "Refresh summary" : "Summarize"}
        </button>
      }
    >
      {error && <p className="text-sm text-red-300">{error}</p>}
      {!error && !summary && <p className="text-sm text-gray-400">Get a plain-language briefing of this page.</p>}
      {summary && <Markdown text={summary} />}
    </Panel>
  );
}
