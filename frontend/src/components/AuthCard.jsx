// Shared frame for the signed-out screens (login, register, password reset).
export default function AuthCard({ title, subtitle, children, onSubmit }) {
  return (
    <div className="relative flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-black overflow-hidden p-4">
      <div className="absolute w-96 h-96 bg-purple-500 rounded-full blur-3xl opacity-30 -top-20 -left-20" />
      <div className="absolute w-96 h-96 bg-indigo-500 rounded-full blur-3xl opacity-30 bottom-0 right-0" />
      <form
        onSubmit={onSubmit}
        className="relative backdrop-blur-xl bg-white/10 border border-white/20 p-10 rounded-2xl shadow-2xl w-full max-w-[400px] text-white"
      >
        <h1 className="text-3xl font-bold mb-2 text-center">{title}</h1>
        {subtitle && <p className="text-center text-gray-300 mb-8">{subtitle}</p>}
        {children}
      </form>
    </div>
  );
}

export const authInput =
  "w-full p-3 mb-4 rounded-lg bg-white/20 border border-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder-gray-300";

export const authButton =
  "w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 disabled:opacity-60 transition duration-300 py-3 rounded-lg font-semibold shadow-lg";

export function AuthMessage({ tone = "error", children }) {
  const cls = tone === "error"
    ? "border-red-400/40 bg-red-900/40 text-red-200"
    : "border-emerald-400/40 bg-emerald-900/30 text-emerald-200";
  return <div role={tone === "error" ? "alert" : "status"} className={`mb-4 rounded-lg border p-3 text-sm ${cls}`}>{children}</div>;
}
