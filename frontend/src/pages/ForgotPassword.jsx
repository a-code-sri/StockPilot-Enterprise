import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import AuthCard, { AuthMessage, authButton, authInput } from "../components/AuthCard";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [emailEnabled, setEmailEnabled] = useState(null);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/auth/options").then((r) => setEmailEnabled(r.data.email_enabled)).catch(() => setEmailEnabled(false));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
    } catch (err) {
      setError(errorMessage(err, "Could not send the request"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="Forgot password" subtitle="We'll help you get back in." onSubmit={submit}>
      {emailEnabled === false ? (
        <AuthMessage tone="ok">
          Password reset emails aren't set up on this server. Ask your administrator to create a reset link for you
          on the <strong>Users &amp; Roles</strong> page.
        </AuthMessage>
      ) : sent ? (
        <AuthMessage tone="ok">
          If that email belongs to an account, a reset link is on its way. It works once and expires soon.
        </AuthMessage>
      ) : (
        <>
          {error && <AuthMessage>{error}</AuthMessage>}
          <label className="sr-only" htmlFor="email">Email</label>
          <input id="email" type="email" required autoComplete="email" className={authInput}
            placeholder="Your account email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button type="submit" disabled={busy || emailEnabled === null} className={authButton}>
            {busy ? "Sending…" : "Send reset link"}
          </button>
        </>
      )}
      <Link to="/" className="block text-center text-sm text-gray-300 mt-6 hover:text-white">Back to sign in</Link>
    </AuthCard>
  );
}
