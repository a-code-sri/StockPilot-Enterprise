import { useCallback, useEffect, useMemo, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import Pager from "../components/Pager";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";
import { dateTime, money } from "../lib/format";

const PAGE_SIZE = 50;

const BADGE = {
  pending: "bg-yellow-500/10 border-yellow-500/30 text-yellow-200",
  packed: "bg-indigo-500/10 border-indigo-500/30 text-indigo-200",
  out_for_delivery: "bg-blue-500/10 border-blue-500/30 text-blue-200",
  delivered: "bg-emerald-500/10 border-emerald-500/30 text-emerald-200",
  failed: "bg-red-500/10 border-red-500/30 text-red-200",
  cancelled: "bg-gray-500/10 border-gray-500/30 text-gray-300",
};

const ACTION_LABEL = {
  pending: "Back to pending",
  packed: "Mark packed",
  out_for_delivery: "Dispatch",
  delivered: "Mark delivered",
  failed: "Mark failed",
  cancelled: "Cancel",
};

const label = (s) => s?.replaceAll("_", " ");

function Badge({ value }) {
  return (
    <span className={`text-xs px-2 py-1 rounded-lg border capitalize ${BADGE[value] || BADGE.cancelled}`}>
      {label(value)}
    </span>
  );
}

const emptyItem = () => ({ inventory_item_id: "", product_name: "", quantity: 1, unit_price: "" });

function CreateDelivery({ inventory, onCreated, onError }) {
  const [orderId, setOrderId] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [remarks, setRemarks] = useState("");
  const [items, setItems] = useState([emptyItem()]);
  const [busy, setBusy] = useState(false);

  const updateItem = (i, patch) => setItems(items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));

  const pickInventory = (i, id) => {
    const inv = inventory.find((x) => String(x.id) === id);
    updateItem(i, inv ? { inventory_item_id: id, product_name: inv.name, unit_price: inv.price } : { inventory_item_id: "" });
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/delivery/", {
        order_id: orderId.trim(),
        customer_id: customerId.trim(),
        remarks: remarks.trim() || null,
        items: items.map((it) => ({
          product_name: it.product_name.trim(),
          quantity: Number(it.quantity),
          unit_price: Number(it.unit_price || 0),
          inventory_item_id: it.inventory_item_id ? Number(it.inventory_item_id) : null,
        })),
      });
      setOrderId("");
      setCustomerId("");
      setRemarks("");
      setItems([emptyItem()]);
      onCreated();
    } catch (err) {
      onError(errorMessage(err, "Could not create delivery"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="New delivery" subtitle="Items linked to inventory are deducted from stock when the delivery is dispatched." className="mb-8">
      <form onSubmit={submit} className="space-y-4">
        <div className="flex flex-wrap gap-3">
          <input className={inputClass} required maxLength={80} placeholder="Order ID" value={orderId} onChange={(e) => setOrderId(e.target.value)} />
          <input className={inputClass} required maxLength={80} placeholder="Customer ID" value={customerId} onChange={(e) => setCustomerId(e.target.value)} />
          <input className={`${inputClass} flex-1 min-w-48`} maxLength={1000} placeholder="Remarks (optional)" value={remarks} onChange={(e) => setRemarks(e.target.value)} />
        </div>
        {items.map((it, i) => (
          <div key={i} className="flex flex-wrap items-center gap-3">
            <select className={inputClass} value={it.inventory_item_id} onChange={(e) => pickInventory(i, e.target.value)} aria-label="Inventory item">
              <option value="">Not from inventory</option>
              {inventory.map((inv) => (
                <option key={inv.id} value={inv.id}>{inv.name} ({inv.quantity} in stock)</option>
              ))}
            </select>
            <input className={inputClass} required maxLength={200} placeholder="Product name" value={it.product_name}
              disabled={Boolean(it.inventory_item_id)} onChange={(e) => updateItem(i, { product_name: e.target.value })} />
            <input className={`${inputClass} w-24`} type="number" min="1" required placeholder="Qty" value={it.quantity}
              onChange={(e) => updateItem(i, { quantity: e.target.value })} />
            <input className={`${inputClass} w-28`} type="number" min="0" step="0.01" placeholder="Unit price" value={it.unit_price}
              onChange={(e) => updateItem(i, { unit_price: e.target.value })} />
            {items.length > 1 && (
              <button type="button" className={buttonClass.small} onClick={() => setItems(items.filter((_, idx) => idx !== i))}>
                Remove
              </button>
            )}
          </div>
        ))}
        <div className="flex gap-3">
          <button type="button" className={buttonClass.secondary} onClick={() => setItems([...items, emptyItem()])}>+ Add item</button>
          <button className={buttonClass.primary} disabled={busy}>{busy ? "Creating…" : "Create delivery"}</button>
        </div>
      </form>
    </Panel>
  );
}

function DeliveryDetail({ orderId, canWrite, onChanged, onError }) {
  const [detail, setDetail] = useState(null);
  const [logs, setLogs] = useState([]);
  const [remark, setRemark] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [d, l] = await Promise.all([
        api.get(`/delivery/${encodeURIComponent(orderId)}`),
        api.get(`/delivery/${encodeURIComponent(orderId)}/logs`),
      ]);
      setDetail(d.data);
      setLogs(l.data);
    } catch (err) {
      onError(errorMessage(err, "Could not load delivery"));
    }
  }, [orderId, onError]);

  useEffect(() => {
    load();
  }, [load]);

  const changeStatus = async (status) => {
    setBusy(true);
    try {
      await api.put(`/delivery/${encodeURIComponent(orderId)}/status`, { status, remark: remark.trim() || null });
      setRemark("");
      await load();
      onChanged();
    } catch (err) {
      onError(errorMessage(err, "Status change failed"));
    } finally {
      setBusy(false);
    }
  };

  if (!detail) return <Panel title={orderId}><p className="text-gray-500 text-sm">Loading…</p></Panel>;

  const total = detail.items.reduce((s, it) => s + it.quantity * it.unit_price, 0);

  return (
    <Panel title={`Order ${detail.order_id}`} subtitle={`Customer ${detail.customer_id}`} action={<Badge value={detail.status} />}>
      <table className="w-full text-sm mb-4">
        <thead className="text-xs text-gray-400 uppercase text-left">
          <tr><th className="pb-2">Product</th><th className="pb-2 text-right">Qty</th><th className="pb-2 text-right">Total</th></tr>
        </thead>
        <tbody>
          {detail.items.map((it, i) => (
            <tr key={i} className="border-t border-gray-800">
              <td className="py-2">
                {it.product_name}
                {it.inventory_item_id && <span className="ml-2 text-xs text-indigo-300">stock-linked</span>}
              </td>
              <td className="py-2 text-right">{it.quantity}</td>
              <td className="py-2 text-right">{money(it.quantity * it.unit_price)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-gray-700"><td className="py-2 text-gray-400" colSpan={2}>Order total</td><td className="py-2 text-right font-semibold">{money(total)}</td></tr>
        </tfoot>
      </table>

      <p className="text-xs text-gray-400 mb-4">
        {detail.stock_deducted ? "Linked stock has been deducted from inventory." : "Linked stock has not been deducted."}
        {detail.remarks && <> · {detail.remarks}</>}
      </p>

      {canWrite && detail.allowed_next.length > 0 && (
        <div className="space-y-2 mb-6">
          <input className={`${inputClass} w-full`} placeholder="Remark for this change (optional)" maxLength={1000}
            value={remark} onChange={(e) => setRemark(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            {detail.allowed_next.map((s) => (
              <button key={s} disabled={busy}
                className={["cancelled", "failed"].includes(s) ? buttonClass.danger : buttonClass.primary}
                onClick={() => changeStatus(s)}>
                {ACTION_LABEL[s] || label(s)}
              </button>
            ))}
          </div>
        </div>
      )}

      <h3 className="text-xs uppercase text-gray-400 mb-2">Status history</h3>
      <ul className="space-y-2 text-sm">
        {logs.map((l) => (
          <li key={l.id} className="flex justify-between gap-3 border-b border-gray-800 pb-2">
            <span>
              <span className="capitalize text-gray-400">{label(l.from_status) || "created"}</span>
              <span className="mx-2 text-gray-600">→</span>
              <span className="capitalize text-indigo-300">{label(l.to_status)}</span>
              {l.remark && <span className="block text-xs text-gray-500">{l.remark}</span>}
            </span>
            <span className="text-xs text-gray-500 whitespace-nowrap">{dateTime(l.timestamp)}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export default function Delivery() {
  const { can } = useAuth();
  const canWrite = can("delivery.write");

  const [tab, setTab] = useState("active");
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [inventory, setInventory] = useState([]);
  const [error, setError] = useState("");

  const fetchRows = useCallback(async () => {
    try {
      const res = await api.get(`/delivery/${tab}`, { params: { limit: PAGE_SIZE, offset } });
      setRows(res.data);
      setTotal(Number(res.headers["x-total-count"] ?? res.data.length));
    } catch (err) {
      setError(errorMessage(err, "Could not load deliveries"));
    }
  }, [tab, offset]);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  useEffect(() => {
    if (!canWrite || !can("inventory.read")) return;
    api.get("/inventory/", { params: { limit: 1000 } }).then((r) => setInventory(r.data)).catch(() => {});
  }, [canWrite, can]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((d) => d.order_id.toLowerCase().includes(q) || d.customer_id.toLowerCase().includes(q));
  }, [rows, search]);

  return (
    <Page title="Delivery" subtitle="Create orders, move them through dispatch and track their history."
      actions={<button className={buttonClass.secondary} onClick={fetchRows}>Refresh</button>}>
      <ErrorBanner message={error} onClose={() => setError("")} />

      {canWrite && <CreateDelivery inventory={inventory} onCreated={() => { setTab("active"); setOffset(0); fetchRows(); }} onError={setError} />}

      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div role="tablist" className="flex gap-6 border-b border-gray-800">
          {[["active", "Active"], ["finished", "Finished"]].map(([id, text]) => (
            <button key={id} role="tab" aria-selected={tab === id}
              onClick={() => { setTab(id); setOffset(0); }}
              className={`pb-2 ${tab === id ? "border-b-2 border-indigo-500 text-indigo-300" : "text-gray-400"}`}>
              {text}
            </button>
          ))}
        </div>
        <input className={`${inputClass} w-64`} placeholder="Filter by order or customer" value={search}
          onChange={(e) => setSearch(e.target.value)} aria-label="Filter" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_440px]">
        <div>
          <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 text-gray-400 text-xs uppercase text-left">
                <tr>
                  <th className="p-3">Order</th>
                  <th className="p-3">Customer</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">{tab === "finished" ? "Completed" : "Updated"}</th>
                  <th className="p-3 text-right">Items</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 && (
                  <tr><td colSpan={5} className="p-6 text-center text-gray-500">No deliveries.</td></tr>
                )}
                {filtered.map((d) => (
                  <tr key={d.order_id}
                    className={`border-t border-gray-800 hover:bg-gray-800/40 cursor-pointer ${selected === d.order_id ? "bg-indigo-500/10" : ""}`}
                    onClick={() => setSelected(d.order_id)}>
                    <td className="p-3 font-mono text-indigo-300">{d.order_id}</td>
                    <td className="p-3">{d.customer_id}</td>
                    <td className="p-3"><Badge value={d.status} /></td>
                    <td className="p-3 text-gray-400">{dateTime(tab === "finished" ? d.completed_at : d.updated_at)}</td>
                    <td className="p-3 text-right">{d.items_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager offset={offset} limit={PAGE_SIZE} total={total} onChange={setOffset} />
        </div>

        {selected ? (
          <DeliveryDetail key={selected} orderId={selected} canWrite={canWrite} onChanged={fetchRows} onError={setError} />
        ) : (
          <Panel title="Select a delivery"><p className="text-sm text-gray-500">Click a row to see items, history and next steps.</p></Panel>
        )}
      </div>
    </Page>
  );
}
