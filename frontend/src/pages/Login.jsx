import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    const result = await login(username.trim(), password);
    setBusy(false);
    if (result.ok) navigate(location.state?.from || "/dashboard", { replace: true });
    else setError(result.error);
  };

  return (
    <div className="relative flex items-center justify-center min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-black overflow-hidden">
      <div className="absolute w-96 h-96 bg-purple-500 rounded-full blur-3xl opacity-30 -top-20 -left-20" />
      <div className="absolute w-96 h-96 bg-indigo-500 rounded-full blur-3xl opacity-30 bottom-0 right-0" />

      <form
        onSubmit={handleSubmit}
        className="relative backdrop-blur-xl bg-white/10 border border-white/20 p-10 rounded-2xl shadow-2xl w-[400px] text-white"
      >
        <h1 className="text-3xl font-bold mb-2 text-center">StockPilot</h1>
        <p className="text-center text-gray-300 mb-8">Smart Manufacturing Control Panel</p>

        {error && (
          <div role="alert" className="mb-4 rounded-lg border border-red-400/40 bg-red-900/40 p-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <label className="sr-only" htmlFor="username">Username</label>
        <input
          id="username"
          autoComplete="username"
          required
          className="w-full p-3 mb-4 rounded-lg bg-white/20 border border-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder-gray-300"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <label className="sr-only" htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          className="w-full p-3 mb-6 rounded-lg bg-white/20 border border-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder-gray-300"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          type="submit"
          disabled={busy}
          className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 disabled:opacity-60 transition duration-300 py-3 rounded-lg font-semibold shadow-lg"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <Link
          to="/register"
          className="block text-center w-full mt-3 border border-white/30 hover:bg-white/10 transition duration-300 py-3 rounded-lg font-semibold"
        >
          Create an account
        </Link>
      </form>
    </div>
  );
}
