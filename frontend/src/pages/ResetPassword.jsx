import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import AuthCard, { AuthMessage, authButton, authInput } from "../components/AuthCard";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("The two passwords don't match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      navigate("/", { replace: true, state: { notice: "Password updated. Sign in with your new password." } });
    } catch (err) {
      setError(errorMessage(err, "Could not reset the password"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="Choose a new password" onSubmit={submit}>
      {!token ? (
        <AuthMessage>This link is incomplete. Open the full link you received, or ask for a new one.</AuthMessage>
      ) : (
        <>
          {error && <AuthMessage>{error}</AuthMessage>}
          <input type="password" required minLength={8} maxLength={72} autoComplete="new-password" className={authInput}
            placeholder="New password (min 8 characters)" value={password} onChange={(e) => setPassword(e.target.value)} />
          <input type="password" required minLength={8} maxLength={72} autoComplete="new-password" className={authInput}
            placeholder="Repeat new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <button type="submit" disabled={busy} className={authButton}>{busy ? "Saving…" : "Set password"}</button>
        </>
      )}
      <Link to="/" className="block text-center text-sm text-gray-300 mt-6 hover:text-white">Back to sign in</Link>
    </AuthCard>
  );
}
