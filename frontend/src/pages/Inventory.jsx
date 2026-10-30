import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";

const STATUSES = [
  ["under_use", "Under use"],
  ["ordered", "Ordered"],
  ["consumed", "Consumed"],
];

const MOVEMENTS = [
  ["add", "Receive stock (+)"],
  ["consume", "Consume (−)"],
  ["deliver", "Deliver (−)"],
  ["order", "Place order (on-order +)"],
  ["return", "Return to stock (+)"],
];

const EMPTY_FORM = { name: "", quantity: "", on_order_quantity: "", price: "", status: "under_use", expiry_date: "" };

const money = (v) => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function MovementForm({ item, onDone, onError }) {
  const [action, setAction] = useState("consume");
  const [quantity, setQuantity] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.put(`/inventory/${item.id}`, { action, quantity: Number(quantity), note: note.trim() || null });
      setQuantity("");
      setNote("");
      onDone();
    } catch (err) {
      onError(errorMessage(err, "Stock update failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-wrap items-center gap-2">
      <select className={inputClass} value={action} onChange={(e) => setAction(e.target.value)} aria-label="Movement">
        {MOVEMENTS.map(([v, l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
      </select>
      <input className={`${inputClass} w-24`} type="number" min="1" required placeholder="Qty"
        value={quantity} onChange={(e) => setQuantity(e.target.value)} aria-label="Quantity" />
      <input className={`${inputClass} w-48`} placeholder="Note (optional)" maxLength={500}
        value={note} onChange={(e) => setNote(e.target.value)} aria-label="Note" />
      <button className={buttonClass.primary} disabled={busy}>{busy ? "Saving…" : "Apply"}</button>
    </form>
  );
}

export default function Inventory() {
  const { can } = useAuth();
  const canWrite = can("inventory.write");

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [selected, setSelected] = useState(null);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");

  const fetchInventory = useCallback(async () => {
    try {
      const res = await api.get("/inventory/", {
        params: { search: search || undefined, status: statusFilter || undefined, limit: 500 },
      });
      setItems(res.data);
      setTotal(Number(res.headers["x-total-count"] ?? res.data.length));
    } catch (err) {
      setError(errorMessage(err, "Failed to load inventory"));
    }
  }, [search, statusFilter]);

  useEffect(() => {
    const t = setTimeout(fetchInventory, 250); // debounce search typing
    return () => clearTimeout(t);
  }, [fetchInventory]);

  const fetchLogs = useCallback(async (item) => {
    try {
      const res = await api.get(`/inventory/${item.id}/logs`);
      setLogs(res.data);
    } catch (err) {
      setError(errorMessage(err, "Failed to load history"));
    }
  }, []);

  const select = (item) => {
    setSelected(item);
    fetchLogs(item);
  };

  const refreshAfterChange = async () => {
    setError("");
    await fetchInventory();
    if (selected) {
      const res = await api.get(`/inventory/${selected.id}`).catch(() => null);
      setSelected(res?.data ?? null);
      if (res) fetchLogs(res.data);
    }
  };

  const createItem = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.post("/inventory/", {
        name: form.name.trim(),
        quantity: Number(form.quantity || 0),
        on_order_quantity: Number(form.on_order_quantity || 0),
        price: Number(form.price || 0),
        status: form.status,
        expiry_date: form.expiry_date || null,
      });
      setForm(EMPTY_FORM);
      fetchInventory();
    } catch (err) {
      setError(errorMessage(err, "Failed to create item"));
    }
  };

  const deleteItem = async (item) => {
    if (!window.confirm(`Delete "${item.name}"? Its history is kept for analytics.`)) return;
    try {
      await api.delete(`/inventory/${item.id}`);
      if (selected?.id === item.id) setSelected(null);
      fetchInventory();
    } catch (err) {
      setError(errorMessage(err, "Failed to delete item"));
    }
  };

  const updateStatus = async (item, status) => {
    try {
      await api.put(`/inventory/${item.id}/status`, { status });
      refreshAfterChange();
    } catch (err) {
      setError(errorMessage(err, "Failed to update status"));
    }
  };

  const setField = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <Page title="Inventory" subtitle={`${total} item${total === 1 ? "" : "s"}`}>
      <ErrorBanner message={error} onClose={() => setError("")} />

      {canWrite && (
        <Panel title="Add item" className="mb-8">
          <form onSubmit={createItem} className="flex flex-wrap gap-3">
            <input className={inputClass} required maxLength={200} placeholder="Name" value={form.name} onChange={setField("name")} />
            <input className={`${inputClass} w-28`} type="number" min="0" placeholder="Quantity" value={form.quantity} onChange={setField("quantity")} />
            <input className={`${inputClass} w-28`} type="number" min="0" placeholder="On order" value={form.on_order_quantity} onChange={setField("on_order_quantity")} />
            <input className={`${inputClass} w-28`} type="number" min="0" step="0.01" placeholder="Price" value={form.price} onChange={setField("price")} />
            <select className={inputClass} value={form.status} onChange={setField("status")} aria-label="Status">
              {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <label className="flex items-center gap-2 text-sm text-gray-400">
              Expiry
              <input className={inputClass} type="date" value={form.expiry_date} onChange={setField("expiry_date")} />
            </label>
            <button className={buttonClass.primary}>Add</button>
          </form>
        </Panel>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <input className={`${inputClass} w-64`} placeholder="Search by name…" value={search}
          onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
        <select className={inputClass} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-800 text-gray-400 text-xs uppercase text-left">
              <tr>
                <th className="p-3">Name</th>
                <th className="p-3 text-right">In stock</th>
                <th className="p-3 text-right">On order</th>
                <th className="p-3 text-right">Price</th>
                <th className="p-3">Expiry</th>
                <th className="p-3">Status</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr><td colSpan={7} className="p-6 text-center text-gray-500">No items.</td></tr>
              )}
              {items.map((item) => (
                <tr key={item.id}
                  className={`border-t border-gray-800 hover:bg-gray-800/40 ${selected?.id === item.id ? "bg-indigo-500/10" : ""}`}>
                  <td className="p-3">
                    <button type="button" className="text-left hover:text-indigo-300" onClick={() => select(item)}>
                      {item.name}
                    </button>
                  </td>
                  <td className={`p-3 text-right ${item.quantity === 0 ? "text-red-300" : ""}`}>{item.quantity}</td>
                  <td className="p-3 text-right text-gray-400">{item.on_order_quantity}</td>
                  <td className="p-3 text-right">{money(item.price)}</td>
                  <td className="p-3 text-gray-400">{item.expiry_date || "—"}</td>
                  <td className="p-3">
                    {canWrite ? (
                      <select className="bg-gray-800 rounded p-1" value={item.status}
                        onChange={(e) => updateStatus(item, e.target.value)} aria-label={`Status of ${item.name}`}>
                        {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    ) : (
                      STATUSES.find(([v]) => v === item.status)?.[1]
                    )}
                  </td>
                  <td className="p-3 whitespace-nowrap space-x-2 text-right">
                    <button type="button" className={buttonClass.small} onClick={() => select(item)}>Manage</button>
                    {canWrite && (
                      <button type="button" className={buttonClass.danger} onClick={() => deleteItem(item)}>Delete</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Panel
          title={selected ? selected.name : "Select an item"}
          subtitle={selected ? `In stock ${selected.quantity} · on order ${selected.on_order_quantity}` : "Click an item to record stock movements and see its history."}
        >
          {selected && (
            <>
              {canWrite && (
                <div className="mb-6">
                  <MovementForm item={selected} onDone={refreshAfterChange} onError={setError} />
                </div>
              )}
              <h3 className="text-xs uppercase text-gray-400 mb-2">History</h3>
              {logs.length === 0 ? (
                <p className="text-gray-500 text-sm">No movements yet.</p>
              ) : (
                <ul className="divide-y divide-gray-800 text-sm max-h-[480px] overflow-y-auto">
                  {logs.map((log) => (
                    <li key={log.id} className="py-2 flex justify-between gap-3">
                      <span>
                        <span className="capitalize">{log.action.replace("_", " ")}</span>
                        {log.quantity != null && <span className="text-gray-300"> · {log.quantity}</span>}
                        {log.detail && <span className="block text-xs text-gray-500">{log.detail}</span>}
                      </span>
                      <span className="text-gray-500 whitespace-nowrap">{new Date(log.timestamp).toLocaleString()}</span>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </Panel>
      </div>
    </Page>
  );
}
