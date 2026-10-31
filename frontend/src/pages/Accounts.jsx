import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import Pager from "../components/Pager";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";
import { dateTime, money } from "../lib/format";

const PAGE_SIZE = 50;
const EMPTY = { amount: "", transaction_type: "credit", source_target: "", category: "", remarks: "" };

function Card({ title, value, tone = "text-gray-200" }) {
  return (
    <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl">
      <h3 className="text-gray-400 text-xs uppercase tracking-wide mb-3">{title}</h3>
      <p className={`text-2xl font-bold ${tone}`}>{value}</p>
    </div>
  );
}

export default function Accounts() {
  const { can } = useAuth();
  const canWrite = can("accounts.write");

  const [transactions, setTransactions] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [typeFilter, setTypeFilter] = useState("");
  const [summary, setSummary] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");

  const fetchTransactions = useCallback(async () => {
    try {
      const res = await api.get("/accounts/", {
        params: { limit: PAGE_SIZE, offset, transaction_type: typeFilter || undefined },
      });
      setTransactions(res.data);
      setTotal(Number(res.headers["x-total-count"] ?? res.data.length));
    } catch (err) {
      setError(errorMessage(err, "Failed to load transactions"));
    }
  }, [offset, typeFilter]);

  const fetchSummary = useCallback(async () => {
    try {
      setSummary((await api.get("/accounts/summary")).data);
    } catch (err) {
      setError(errorMessage(err, "Failed to load summary"));
    }
  }, []);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const refresh = () => {
    fetchTransactions();
    fetchSummary();
  };

  const createTransaction = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/accounts/", {
        ...form,
        amount: Number(form.amount),
        source_target: form.source_target.trim(),
        category: form.category.trim(),
        remarks: form.remarks.trim() || null,
      });
      setForm(EMPTY);
      setOffset(0);
      refresh();
    } catch (err) {
      setError(errorMessage(err, "Failed to record transaction"));
    }
  };

  const deleteTransaction = async (t) => {
    if (!window.confirm(`Delete this ${t.transaction_type} of ${money(t.amount)}?`)) return;
    try {
      await api.delete(`/accounts/${t.id}`);
      refresh();
    } catch (err) {
      setError(errorMessage(err, "Failed to delete transaction"));
    }
  };

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <Page title="Accounts" subtitle="Income and expense ledger">
      <ErrorBanner message={error} onClose={() => setError("")} />

      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 mb-8">
          <Card title="Current balance" value={money(summary.current_balance)} tone="text-indigo-300" />
          <Card title="Total credit" value={money(summary.total_credit)} tone="text-emerald-300" />
          <Card title="Total debit" value={money(summary.total_debit)} tone="text-red-300" />
          <Card title="Net, last 30 days" value={money(summary.last_30_days_net)} />
        </div>
      )}

      {canWrite && (
        <Panel title="Record transaction" className="mb-8">
          <form onSubmit={createTransaction} className="flex flex-wrap gap-3">
            <input className={`${inputClass} w-32`} type="number" min="0.01" step="0.01" required placeholder="Amount"
              value={form.amount} onChange={set("amount")} />
            <select className={inputClass} value={form.transaction_type} onChange={set("transaction_type")} aria-label="Type">
              <option value="credit">Credit (income)</option>
              <option value="debit">Debit (expense)</option>
            </select>
            <input className={inputClass} required maxLength={200} placeholder="Customer / supplier"
              value={form.source_target} onChange={set("source_target")} />
            <input className={inputClass} required maxLength={100} placeholder="Category"
              value={form.category} onChange={set("category")} />
            <input className={`${inputClass} flex-1 min-w-48`} maxLength={1000} placeholder="Remarks (optional)"
              value={form.remarks} onChange={set("remarks")} />
            <button className={buttonClass.primary}>Add</button>
          </form>
        </Panel>
      )}

      <div className="flex gap-3 mb-4">
        <select className={inputClass} value={typeFilter} aria-label="Filter by type"
          onChange={(e) => { setTypeFilter(e.target.value); setOffset(0); }}>
          <option value="">All transactions</option>
          <option value="credit">Credits only</option>
          <option value="debit">Debits only</option>
        </select>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400 text-xs uppercase text-left">
            <tr>
              <th className="p-3">Date</th>
              <th className="p-3">Type</th>
              <th className="p-3 text-right">Amount</th>
              <th className="p-3">Customer / supplier</th>
              <th className="p-3">Category</th>
              <th className="p-3">Remarks</th>
              {canWrite && <th className="p-3" />}
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 && (
              <tr><td colSpan={7} className="p-6 text-center text-gray-500">No transactions.</td></tr>
            )}
            {transactions.map((t) => (
              <tr key={t.id} className="border-t border-gray-800 hover:bg-gray-800/40">
                <td className="p-3 whitespace-nowrap text-gray-400">{dateTime(t.date)}</td>
                <td className={`p-3 capitalize ${t.transaction_type === "credit" ? "text-emerald-400" : "text-red-400"}`}>
                  {t.transaction_type}
                </td>
                <td className="p-3 text-right">{money(t.amount)}</td>
                <td className="p-3">{t.source_target}</td>
                <td className="p-3">{t.category}</td>
                <td className="p-3 text-gray-400">{t.remarks}</td>
                {canWrite && (
                  <td className="p-3 text-right">
                    <button className={buttonClass.danger} onClick={() => deleteTransaction(t)}>Delete</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pager offset={offset} limit={PAGE_SIZE} total={total} onChange={setOffset} />
    </Page>
  );
}
