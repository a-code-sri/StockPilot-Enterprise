import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { errorMessage } from "../api";

export default function Register() {
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.post("/auth/register", { ...form, username: form.username.trim() });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err, "Registration failed"));
    } finally {
      setBusy(false);
    }
  };

  const input = "w-full p-3 mb-3 rounded bg-white/20 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-400";

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-900 to-black text-white">
      <form onSubmit={handleRegister} className="bg-white/10 backdrop-blur-xl p-8 rounded-xl w-96">
        <h2 className="text-2xl font-bold mb-6 text-center">Create Account</h2>

        {done ? (
          <div className="space-y-4 text-sm">
            <p className="rounded border border-emerald-400/40 bg-emerald-900/30 p-3 text-emerald-200">
              Account created. An administrator must assign you a role before you can see business data.
            </p>
            <button type="button" onClick={() => navigate("/")} className="w-full bg-indigo-600 py-2 rounded">
              Go to sign in
            </button>
          </div>
        ) : (
          <>
            {error && (
              <div role="alert" className="mb-3 rounded border border-red-400/40 bg-red-900/40 p-3 text-sm text-red-200">
                {error}
              </div>
            )}
            <input className={input} type="email" required placeholder="Email" autoComplete="email"
              value={form.email} onChange={set("email")} />
            <input className={input} required minLength={3} maxLength={50} pattern="[A-Za-z0-9_.\-]+"
              title="Letters, numbers, dot, dash or underscore" placeholder="Username" autoComplete="username"
              value={form.username} onChange={set("username")} />
            <input className={`${input} mb-1`} type="password" required minLength={8} maxLength={72}
              placeholder="Password (min 8 characters)" autoComplete="new-password"
              value={form.password} onChange={set("password")} />
            <p className="text-xs text-gray-400 mb-4">At least 8 characters.</p>
            <button type="submit" disabled={busy} className="w-full bg-indigo-600 disabled:opacity-60 py-2 rounded">
              {busy ? "Creating…" : "Register"}
            </button>
            <Link to="/" className="block text-center text-sm text-gray-300 mt-4 hover:text-white">
              Back to sign in
            </Link>
          </>
        )}
      </form>
    </div>
  );
}
