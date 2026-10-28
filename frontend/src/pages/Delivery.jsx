import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import { MOCK_MODE } from "../config";

const STATUS_OPTIONS = [
  "pending",
  "packed",
  "out_for_delivery",
  "delivered",
  "failed",
  "cancelled",
];

function fmtDate(s) {
  if (!s) return "-";
  try {
    return new Date(s).toLocaleString();
  } catch {
    return String(s);
  }
}

function Badge({ value }) {
  const map = {
    pending: "bg-yellow-500/10 border-yellow-500/30 text-yellow-200",
    packed: "bg-indigo-500/10 border-indigo-500/30 text-indigo-200",
    out_for_delivery: "bg-blue-500/10 border-blue-500/30 text-blue-200",
    delivered: "bg-emerald-500/10 border-emerald-500/30 text-emerald-200",
    failed: "bg-red-500/10 border-red-500/30 text-red-200",
    cancelled: "bg-gray-500/10 border-gray-500/30 text-gray-200",
  };

  const cls = map[value] || "bg-gray-500/10 border-gray-500/30 text-gray-200";

  return (
    <span className={`text-xs px-2 py-1 rounded-lg border capitalize ${cls}`}>
      {value?.replaceAll("_", " ")}
    </span>
  );
}

function Modal({ open, title, onClose, children }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6">
      <div className="w-full max-w-2xl bg-gray-950 border border-gray-800 rounded-2xl shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <div className="font-semibold text-gray-100">{title}</div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition"
          >
            ✕
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export default function Delivery() {
  const [activeTab, setActiveTab] = useState("active");

  const [search, setSearch] = useState("");

  const [activeDeliveries, setActiveDeliveries] = useState([]);
  const [finishedDeliveries, setFinishedDeliveries] = useState([]);

  const [selectedOrderId, setSelectedOrderId] = useState(null);

  const [cartOpen, setCartOpen] = useState(false);
  const [cartItems, setCartItems] = useState([]);

  const [logs, setLogs] = useState([]);

  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const titleGradient =
    "bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent";

  // ---------- Mock store (in-memory)
  const [mockStore, setMockStore] = useState(() => {
    const now = new Date().toISOString();
    return {
      active: [
        {
          order_id: "ORD-1001",
          customer_id: "CUST-10",
          status: "pending",
          created_at: now,
          updated_at: now,
          completed_at: null,
          items_count: 3,
        },
        {
          order_id: "ORD-1002",
          customer_id: "CUST-11",
          status: "out_for_delivery",
          created_at: now,
          updated_at: now,
          completed_at: null,
          items_count: 2,
        },
      ],
      finished: [
        {
          order_id: "ORD-0999",
          customer_id: "CUST-02",
          status: "delivered",
          created_at: now,
          updated_at: now,
          completed_at: now,
          items_count: 1,
        },
      ],
      itemsByOrder: {
        "ORD-1001": [
          { product_name: "Widget A", quantity: 2, unit_price: 50 },
          { product_name: "Widget B", quantity: 1, unit_price: 80 },
        ],
        "ORD-1002": [
          { product_name: "Packaging", quantity: 10, unit_price: 2 },
          { product_name: "Tape", quantity: 3, unit_price: 1.5 },
        ],
        "ORD-0999": [{ product_name: "Spare Part", quantity: 1, unit_price: 120 }],
      },
      logsByOrder: {
        "ORD-1001": [
          {
            id: 1,
            from_status: null,
            to_status: "pending",
            remark: "Delivery created",
            timestamp: now,
          },
        ],
        "ORD-1002": [
          {
            id: 1,
            from_status: null,
            to_status: "pending",
            remark: "Delivery created",
            timestamp: now,
          },
          {
            id: 2,
            from_status: "pending",
            to_status: "out_for_delivery",
            remark: "Handed to rider",
            timestamp: now,
          },
        ],
        "ORD-0999": [
          {
            id: 1,
            from_status: null,
            to_status: "pending",
            remark: "Delivery created",
            timestamp: now,
          },
          {
            id: 2,
            from_status: "pending",
            to_status: "delivered",
            remark: "Delivered successfully",
            timestamp: now,
          },
        ],
      },
    };
  });

  const clearMessages = () => {
    setError("");
    setInfo("");
  };

  const extractErrorDetail = (e) => {
    const detail =
      e?.response?.data?.detail ||
      e?.message ||
      "Something went wrong. Please try again.";
    return typeof detail === "string" ? detail : JSON.stringify(detail);
  };

  // ---------- Fetch lists
  const fetchActive = async () => {
    clearMessages();

    if (MOCK_MODE) {
      setActiveDeliveries(mockStore.active);
      return;
    }

    try {
      const res = await api.get("/delivery/active");
      setActiveDeliveries(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const fetchFinished = async () => {
    clearMessages();

    if (MOCK_MODE) {
      setFinishedDeliveries(mockStore.finished);
      return;
    }

    try {
      const res = await api.get("/delivery/finished");
      setFinishedDeliveries(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  useEffect(() => {
    fetchActive();
    fetchFinished();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- Derived: filtered rows
  const filteredActive = useMemo(() => {
    if (!search.trim()) return activeDeliveries;
    const q = search.trim().toLowerCase();
    return activeDeliveries.filter(
      (d) =>
        d.order_id.toLowerCase().includes(q) ||
        d.customer_id.toLowerCase().includes(q)
    );
  }, [activeDeliveries, search]);

  const filteredFinished = useMemo(() => {
    if (!search.trim()) return finishedDeliveries;
    const q = search.trim().toLowerCase();
    return finishedDeliveries.filter(
      (d) =>
        d.order_id.toLowerCase().includes(q) ||
        d.customer_id.toLowerCase().includes(q)
    );
  }, [finishedDeliveries, search]);

  // ---------- Items modal
  const openCartItems = async (orderId) => {
    clearMessages();
    setSelectedOrderId(orderId);

    if (MOCK_MODE) {
      setCartItems(mockStore.itemsByOrder[orderId] || []);
      setCartOpen(true);
      return;
    }

    try {
      const res = await api.get(`/delivery/${orderId}/items`);
      setCartItems(res.data);
      setCartOpen(true);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  // ---------- Logs tab
  const openLogs = async (orderId) => {
    clearMessages();
    setSelectedOrderId(orderId);

    if (MOCK_MODE) {
      setLogs(mockStore.logsByOrder[orderId] || []);
      setActiveTab("logs");
      return;
    }

    try {
      const res = await api.get(`/delivery/${orderId}/logs`);
      setLogs(res.data);
      setActiveTab("logs");
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  // ---------- Update status
  const updateStatus = async (orderId, newStatus) => {
    clearMessages();

    const remark = window.prompt("Remark (optional):") || null;

    if (MOCK_MODE) {
      setMockStore((prev) => {
        const now = new Date().toISOString();

        // find in active or finished
        const inActive = prev.active.find((d) => d.order_id === orderId);
        const inFinished = prev.finished.find((d) => d.order_id === orderId);
        const current = inActive || inFinished;
        if (!current) return prev;

        const fromStatus = current.status;
        const updatedRow = {
          ...current,
          status: newStatus,
          updated_at: now,
          completed_at:
            ["delivered", "failed", "cancelled"].includes(newStatus) ? now : null,
        };

        // move between lists if needed
        let newActive = prev.active.filter((d) => d.order_id !== orderId);
        let newFinished = prev.finished.filter((d) => d.order_id !== orderId);

        if (["delivered", "failed", "cancelled"].includes(newStatus)) {
          newFinished = [updatedRow, ...newFinished];
        } else {
          newActive = [updatedRow, ...newActive];
        }

        const logsList = prev.logsByOrder[orderId] || [];
        const newLog = {
          id: logsList.length + 1,
          from_status: fromStatus,
          to_status: newStatus,
          remark,
          timestamp: now,
        };

        return {
          ...prev,
          active: newActive,
          finished: newFinished,
          logsByOrder: {
            ...prev.logsByOrder,
            [orderId]: [newLog, ...logsList],
          },
        };
      });

      setInfo("Status updated (mock).");
      // refresh UI lists from mock store
      setTimeout(() => {
        setActiveDeliveries((_) => (mockStore.active));
        setFinishedDeliveries((_) => (mockStore.finished));
      }, 0);

      return;
    }

    try {
      await api.put(`/delivery/${orderId}/status`, {
        status: newStatus,
        remark,
      });

      setInfo("Status updated.");
      await fetchActive();
      await fetchFinished();

      // if currently viewing logs of this order, refresh them too
      if (activeTab === "logs" && selectedOrderId === orderId) {
        await openLogs(orderId);
      }
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const renderTable = (rows, mode) => {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
            <tr>
              <th className="p-4">Order ID</th>
              <th className="p-4">Customer ID</th>
              <th className="p-4">Status</th>
              <th className="p-4">Time</th>
              <th className="p-4">Items</th>
              <th className="p-4">Actions</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((d) => (
              <tr
                key={d.order_id}
                className="border-t border-gray-800 hover:bg-gray-800/40 transition"
              >
                <td className="p-4 font-mono text-indigo-300">{d.order_id}</td>
                <td className="p-4">{d.customer_id}</td>
                <td className="p-4">
                  <Badge value={d.status} />
                </td>
                <td className="p-4 text-gray-300">
                  {mode === "finished" ? fmtDate(d.completed_at) : fmtDate(d.updated_at)}
                </td>
                <td className="p-4">
                  <span className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200">
                    {d.items_count} items
                  </span>
                </td>

                <td className="p-4 space-x-2">
                  <button
                    onClick={() => openCartItems(d.order_id)}
                    className="bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded-xl transition"
                  >
                    View Cart Items
                  </button>

                  <button
                    onClick={() => openLogs(d.order_id)}
                    className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-3 py-2 rounded-xl transition"
                  >
                    Logs
                  </button>

                  <select
                    className="bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 outline-none"
                    defaultValue={d.status}
                    onChange={(e) => updateStatus(d.order_id, e.target.value)}
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s.replaceAll("_", " ")}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}

            {rows.length === 0 && (
              <tr>
                <td className="p-6 text-gray-500" colSpan={6}>
                  No deliveries found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    );
  };

  const cartTotal = useMemo(() => {
    return (cartItems || []).reduce(
      (sum, it) => sum + Number(it.quantity || 0) * Number(it.unit_price || 0),
      0
    );
  }, [cartItems]);

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className={`text-4xl font-bold mb-2 ${titleGradient}`}>Delivery Module</h1>
            <p className="text-gray-400">
              Track active and finished deliveries, view cart items and status logs.
            </p>
          </div>

          <button
            onClick={() => {
              fetchActive();
              fetchFinished();
            }}
            className="bg-gray-900 border border-gray-800 hover:border-indigo-500/60 px-4 py-2 rounded-xl transition"
          >
            Refresh
          </button>
        </div>

        {/* Search */}
        <div className="mt-6 bg-gray-900 border border-gray-800 p-5 rounded-2xl">
          <label className="text-xs text-gray-400">Search (order_id / customer_id)</label>
          <input
            className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
            placeholder="e.g. ORD-1001 or CUST-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Alerts */}
        {error && (
          <div className="mt-6 bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Error</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
        )}
        {info && (
          <div className="mt-6 bg-emerald-950/30 border border-emerald-900 text-emerald-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Success</div>
            <div className="text-sm mt-1">{info}</div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex mt-8 mb-8 space-x-8 border-b border-gray-800">
          <button
            onClick={() => setActiveTab("active")}
            className={`pb-2 ${
              activeTab === "active"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Active Deliveries
          </button>

          <button
            onClick={() => setActiveTab("finished")}
            className={`pb-2 ${
              activeTab === "finished"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Finished Deliveries
          </button>

          <button
            onClick={() => setActiveTab("logs")}
            className={`pb-2 ${
              activeTab === "logs"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Logs
          </button>
        </div>

        {/* Active */}
        {activeTab === "active" && renderTable(filteredActive, "active")}

        {/* Finished */}
        {activeTab === "finished" && renderTable(filteredFinished, "finished")}

        {/* Logs */}
        {activeTab === "logs" && (
          <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">
                  Delivery Logs {selectedOrderId ? `• ${selectedOrderId}` : ""}
                </h2>
                <p className="text-sm text-gray-400 mt-1">
                  Click “Logs” on a delivery to load its status transitions.
                </p>
              </div>
              {selectedOrderId && (
                <button
                  onClick={() => openLogs(selectedOrderId)}
                  className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-5 py-2.5 rounded-xl transition"
                >
                  Refresh Logs
                </button>
              )}
            </div>

            <div className="mt-5 space-y-3">
              {logs.map((l) => (
                <div
                  key={l.id}
                  className="bg-gray-950 border border-gray-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3"
                >
                  <div className="text-sm">
                    <div className="text-gray-200">
                      <span className="text-gray-400">From:</span>{" "}
                      {l.from_status || "—"}{" "}
                      <span className="text-gray-500 mx-2">→</span>
                      <span className="text-gray-400">To:</span>{" "}
                      <span className="text-indigo-300">{l.to_status}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {l.remark || "No remark"}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">{fmtDate(l.timestamp)}</div>
                </div>
              ))}

              {logs.length === 0 && (
                <div className="text-gray-500">No logs to display.</div>
              )}
            </div>
          </div>
        )}

        {/* Cart items modal */}
        <Modal
          open={cartOpen}
          title={`Cart Items • ${selectedOrderId || ""}`}
          onClose={() => setCartOpen(false)}
        >
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
                <tr>
                  <th className="p-4">Product</th>
                  <th className="p-4">Qty</th>
                  <th className="p-4">Unit Price</th>
                  <th className="p-4">Total</th>
                </tr>
              </thead>
              <tbody>
                {cartItems.map((it, idx) => (
                  <tr key={idx} className="border-t border-gray-800">
                    <td className="p-4">{it.product_name}</td>
                    <td className="p-4">{it.quantity}</td>
                    <td className="p-4">${Number(it.unit_price).toFixed(2)}</td>
                    <td className="p-4">
                      ${(Number(it.quantity) * Number(it.unit_price)).toFixed(2)}
                    </td>
                  </tr>
                ))}
                {cartItems.length === 0 && (
                  <tr>
                    <td className="p-6 text-gray-500" colSpan={4}>
                      No items.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-gray-400">
              Total: <span className="text-indigo-300 font-semibold">${cartTotal.toFixed(2)}</span>
            </div>
            <button
              onClick={() => setCartOpen(false)}
              className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-5 py-2.5 rounded-xl transition"
            >
              Close
            </button>
          </div>
        </Modal>
      </div>
    </div>
  );
}