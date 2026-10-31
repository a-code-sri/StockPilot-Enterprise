import { useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";

export default function Account() {
  const { user, replaceToken } = useAuth();
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setDone(false);
    if (form.next !== form.confirm) {
      setError("The new passwords don't match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await api.post("/auth/change-password", { current_password: form.current, new_password: form.next });
      replaceToken(res.data.access_token);
      setForm({ current: "", next: "", confirm: "" });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err, "Could not change password"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="My account">
      <ErrorBanner message={error} onClose={() => setError("")} />
      <div className="grid gap-6 lg:grid-cols-2 max-w-5xl">
        <Panel title="Profile">
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
            <dt className="text-gray-400">Username</dt><dd>{user.username}</dd>
            <dt className="text-gray-400">Email</dt><dd>{user.email}</dd>
            <dt className="text-gray-400">Roles</dt><dd>{user.roles.map((r) => r.name).join(", ") || "none"}</dd>
            <dt className="text-gray-400">Permissions</dt>
            <dd className="text-gray-300">{user.permissions.join(", ") || "none — ask an administrator for a role"}</dd>
          </dl>
        </Panel>

        <Panel title="Change password" subtitle="You stay signed in here; other devices and browsers are signed out.">
          {done && <p role="status" className="mb-4 text-sm text-emerald-300">Password changed.</p>}
          <form onSubmit={submit} className="space-y-3">
            <input className={`${inputClass} w-full`} type="password" required autoComplete="current-password"
              placeholder="Current password" value={form.current} onChange={set("current")} />
            <input className={`${inputClass} w-full`} type="password" required minLength={8} maxLength={72}
              autoComplete="new-password" placeholder="New password (min 8 characters)" value={form.next} onChange={set("next")} />
            <input className={`${inputClass} w-full`} type="password" required minLength={8} maxLength={72}
              autoComplete="new-password" placeholder="Repeat new password" value={form.confirm} onChange={set("confirm")} />
            <button className={buttonClass.primary} disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
          </form>
        </Panel>
      </div>
    </Page>
  );
}
