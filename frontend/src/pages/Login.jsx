import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import AuthCard, { AuthMessage, authButton, authInput } from "../components/AuthCard";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [registrationEnabled, setRegistrationEnabled] = useState(true);

  useEffect(() => {
    api.get("/auth/options").then((r) => setRegistrationEnabled(r.data.registration_enabled)).catch(() => {});
  }, []);

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
    <AuthCard title="StockPilot" subtitle="Smart Manufacturing Control Panel" onSubmit={handleSubmit}>
      {location.state?.notice && <AuthMessage tone="ok">{location.state.notice}</AuthMessage>}
      {error && <AuthMessage>{error}</AuthMessage>}

      <label className="sr-only" htmlFor="username">Username</label>
      <input id="username" autoComplete="username" required className={authInput} placeholder="Username"
        value={username} onChange={(e) => setUsername(e.target.value)} />

      <label className="sr-only" htmlFor="password">Password</label>
      <input id="password" type="password" autoComplete="current-password" required className={`${authInput} mb-2`}
        placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <div className="text-right mb-6">
        <Link to="/forgot-password" className="text-sm text-gray-300 hover:text-white">Forgot password?</Link>
      </div>

      <button type="submit" disabled={busy} className={authButton}>{busy ? "Signing in…" : "Sign in"}</button>

      {registrationEnabled && (
        <Link to="/register"
          className="block text-center w-full mt-3 border border-white/30 hover:bg-white/10 transition duration-300 py-3 rounded-lg font-semibold">
          Create an account
        </Link>
      )}
    </AuthCard>
  );
}
