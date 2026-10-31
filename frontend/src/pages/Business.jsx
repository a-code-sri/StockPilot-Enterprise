import { useCallback, useEffect, useRef, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";
import { dateTime } from "../lib/format";

const STATUS = {
  unverified: ["Not verified", "bg-gray-500/10 border-gray-500/40 text-gray-300", "Fix the problems listed below and save again."],
  format_verified: ["Checks passed — awaiting review", "bg-yellow-500/10 border-yellow-500/40 text-yellow-200",
    "The numbers are well-formed and consistent. An administrator should compare them with the registration certificates and approve."],
  verified: ["Verified", "bg-emerald-500/10 border-emerald-500/40 text-emerald-200", "Registration confirmed by an administrator."],
  rejected: ["Rejected", "bg-red-500/10 border-red-500/40 text-red-200", "An administrator rejected the registration. See the review notes."],
};

const FIELDS = ["legal_name", "trade_name", "gstin", "pan", "cin", "state_code", "address", "email", "phone"];

function StatusBadge({ status }) {
  const [text, cls] = STATUS[status] || STATUS.unverified;
  return <span className={`text-xs px-2.5 py-1 rounded-full border ${cls}`}>{text}</span>;
}

function CheckReport({ report }) {
  if (!report) return null;
  return (
    <div className="space-y-2 text-sm">
      {report.errors.map((e) => <p key={e} className="text-red-300">✕ {e}</p>)}
      {report.warnings.map((w) => <p key={w} className="text-yellow-300">! {w}</p>)}
      {report.valid && report.errors.length === 0 && <p className="text-emerald-300">✓ All automatic checks passed.</p>}
      {report.details?.gstin?.state && (
        <p className="text-gray-400">GSTIN registered in {report.details.gstin.state}; PAN holder type: {report.details.pan?.holder_type || "—"}.</p>
      )}
      {report.details?.cin?.company_class && (
        <p className="text-gray-400">
          CIN: {report.details.cin.company_class}, incorporated {report.details.cin.incorporation_year}
          {report.details.cin.listed ? ", listed" : ""}.
        </p>
      )}
    </div>
  );
}

export default function Business() {
  const { can } = useAuth();
  const canManage = can("business.manage");

  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState(Object.fromEntries(FIELDS.map((f) => [f, ""])));
  const [states, setStates] = useState([]);
  const [preview, setPreview] = useState(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const previewTimer = useRef(null);

  const load = useCallback(async () => {
    try {
      const [p, st] = await Promise.all([api.get("/business/profile"), api.get("/business/states")]);
      setProfile(p.data);
      setStates(st.data);
      if (p.data.configured) setForm(Object.fromEntries(FIELDS.map((f) => [f, p.data[f] ?? ""])));
    } catch (err) {
      setError(errorMessage(err, "Could not load business profile"));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Live feedback while typing registration numbers (nothing is saved).
  useEffect(() => {
    if (!canManage || !(form.gstin || form.pan || form.cin)) {
      setPreview(null);
      return;
    }
    clearTimeout(previewTimer.current);
    previewTimer.current = setTimeout(async () => {
      try {
        const res = await api.post("/business/validate", {
          legal_name: form.legal_name, gstin: form.gstin || null, pan: form.pan || null,
          cin: form.cin || null, state_code: form.state_code || null,
        });
        setPreview(res.data);
      } catch {
        setPreview(null);
      }
    }, 400);
    return () => clearTimeout(previewTimer.current);
  }, [canManage, form.legal_name, form.gstin, form.pan, form.cin, form.state_code]);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const body = Object.fromEntries(FIELDS.map((f) => [f, form[f]?.trim?.() || null]));
      body.legal_name = form.legal_name.trim();
      const res = await api.put("/business/profile", body);
      setProfile(res.data);
    } catch (err) {
      setError(errorMessage(err, "Could not save profile"));
    } finally {
      setSaving(false);
    }
  };

  const review = async (decision) => {
    try {
      const res = await api.post("/business/profile/review", { decision, notes: notes.trim() || null });
      setProfile(res.data);
      setNotes("");
    } catch (err) {
      setError(errorMessage(err, "Review failed"));
    }
  };

  const UPPERCASE = new Set(["gstin", "pan", "cin"]);
  const set = (field) => (e) =>
    setForm({ ...form, [field]: UPPERCASE.has(field) ? e.target.value.toUpperCase() : e.target.value });

  const status = profile?.verification_status || "unverified";

  return (
    <Page title="Business Profile" subtitle="Your company's legal identity and registration verification.">
      <ErrorBanner message={error} onClose={() => setError("")} />

      {profile && (
        <Panel className="mb-8" title={profile.configured ? profile.legal_name : "No business profile yet"}
          subtitle={profile.configured ? STATUS[status][2] : canManage ? "Fill in the form below to register your business." : "An administrator has not set this up yet."}
          action={profile.configured && <StatusBadge status={status} />}>
          {profile.configured ? (
            <div className="grid gap-6 lg:grid-cols-2">
              <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
                <dt className="text-gray-400">GSTIN</dt><dd className="font-mono">{profile.gstin || "—"}</dd>
                <dt className="text-gray-400">PAN</dt><dd className="font-mono">{profile.pan || "—"}</dd>
                <dt className="text-gray-400">CIN</dt><dd className="font-mono">{profile.cin || "—"}</dd>
                <dt className="text-gray-400">State</dt><dd>{profile.state || "—"}</dd>
                <dt className="text-gray-400">Last checked</dt><dd>{dateTime(profile.checked_at)}</dd>
                {profile.reviewed_at && (<><dt className="text-gray-400">Reviewed</dt><dd>{dateTime(profile.reviewed_at)} by {profile.reviewed_by || "—"}</dd></>)}
                {profile.review_notes && (<><dt className="text-gray-400">Notes</dt><dd>{profile.review_notes}</dd></>)}
              </dl>
              <div>
                <h3 className="text-xs uppercase text-gray-400 mb-2">Automatic checks</h3>
                <CheckReport report={profile.verification_report} />
                {canManage && status !== "unverified" && (
                  <div className="mt-5 space-y-2">
                    <textarea className={`${inputClass} w-full`} maxLength={2000} placeholder="Review notes (e.g. certificate reference)"
                      value={notes} onChange={(e) => setNotes(e.target.value)} />
                    <div className="flex gap-2">
                      <button className={buttonClass.primary} disabled={status === "verified"} onClick={() => review("approve")}>
                        Approve — I checked the certificates
                      </button>
                      <button className={buttonClass.danger} disabled={status === "rejected"} onClick={() => review("reject")}>Reject</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </Panel>
      )}

      {canManage && (
        <Panel title={profile?.configured ? "Edit details" : "Register business"}
          subtitle="Changing GSTIN, PAN, CIN, state or legal name re-runs the checks and resets approval.">
          <form onSubmit={save} className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-3">
              <input className={`${inputClass} w-full`} required minLength={2} maxLength={200} placeholder="Legal name (as registered)"
                value={form.legal_name} onChange={set("legal_name")} />
              <input className={`${inputClass} w-full`} maxLength={200} placeholder="Trade name (optional)" value={form.trade_name} onChange={set("trade_name")} />
              <div className="grid grid-cols-2 gap-3">
                <input className={`${inputClass} font-mono`} maxLength={15} placeholder="GSTIN (15 chars)" value={form.gstin} onChange={set("gstin")} />
                <input className={`${inputClass} font-mono`} maxLength={10} placeholder="PAN (10 chars)" value={form.pan} onChange={set("pan")} />
                <input className={`${inputClass} font-mono`} maxLength={21} placeholder="CIN (companies, optional)" value={form.cin} onChange={set("cin")} />
                <select className={inputClass} value={form.state_code} onChange={set("state_code")} aria-label="State">
                  <option value="">State (from GSTIN)</option>
                  {states.map((s) => <option key={s.code} value={s.code}>{s.code} — {s.name}</option>)}
                </select>
              </div>
              <textarea className={`${inputClass} w-full`} maxLength={1000} placeholder="Registered address" value={form.address} onChange={set("address")} />
              <div className="grid grid-cols-2 gap-3">
                <input className={inputClass} type="email" placeholder="Contact email" value={form.email} onChange={set("email")} />
                <input className={inputClass} maxLength={30} placeholder="Phone" value={form.phone} onChange={set("phone")} />
              </div>
              <button className={buttonClass.primary} disabled={saving}>{saving ? "Saving…" : "Save and verify"}</button>
            </div>
            <div>
              <h3 className="text-xs uppercase text-gray-400 mb-2">Live check</h3>
              {preview ? <CheckReport report={preview} /> : <p className="text-sm text-gray-500">Enter a GSTIN or PAN to check it as you type.</p>}
              <p className="text-xs text-gray-500 mt-6">
                Checks run offline: GSTIN structure and checksum, PAN format and holder type, CIN structure, and consistency
                between them. They catch typos and mismatches but cannot confirm the business is active on the GST portal —
                that is the reviewer's job.
              </p>
            </div>
          </form>
        </Panel>
      )}
    </Page>
  );
}
