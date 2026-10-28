import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import { MOCK_MODE } from "../config";

export default function Inventory() {
  const [items, setItems] = useState([]);
  const [activeTab, setActiveTab] = useState("inventory");
  const [logs, setLogs] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);

  const [form, setForm] = useState({
    name: "",
    quantity: "",
    price: "",
    status: "under_use",
  });

  const [error, setError] = useState("");

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      setError("");

      if (MOCK_MODE) {
        setItems([
          {
            id: 1,
            name: "Steel",
            quantity: 100,
            price: 50,
            status: "under_use",
          },
          {
            id: 2,
            name: "Plastic",
            quantity: 40,
            price: 20,
            status: "ordered",
          },
        ]);
        return;
      }

      const res = await api.get("/inventory/");
      setItems(res.data);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to load inventory"
      );
    }
  };

  const fetchLogs = async (name) => {
    try {
      setError("");
      setSelectedItem(name);

      if (MOCK_MODE) {
        setLogs([
          {
            action: "add",
            quantity: 50,
            timestamp: "2026-08-01",
          },
          {
            action: "consume",
            quantity: 10,
            timestamp: "2026-08-02",
          },
          {
            action: "status_change",
            quantity: 40,
            timestamp: "2026-08-03",
          },
        ]);
      } else {
        const encodedName = encodeURIComponent(name);

        const res = await api.get(
          `/inventory/${encodedName}/logs`
        );

        setLogs(res.data);
      }

      setActiveTab("logs");
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to load inventory logs"
      );
    }
  };

  const createItem = async () => {
    try {
      setError("");

      if (!form.name.trim()) {
        setError("Item name is required");
        return;
      }

      if (form.quantity === "" || Number(form.quantity) < 0) {
        setError("Quantity must be zero or greater");
        return;
      }

      if (form.price === "" || Number(form.price) < 0) {
        setError("Price must be zero or greater");
        return;
      }

      if (MOCK_MODE) {
        setItems([
          ...items,
          {
            ...form,
            id: items.length + 1,
            quantity: Number(form.quantity),
            price: Number(form.price),
          },
        ]);
      } else {
        await api.post("/inventory/", {
          name: form.name.trim(),
          quantity: Number(form.quantity),
          price: Number(form.price),
          status: form.status,
        });

        await fetchInventory();
      }

      setForm({
        name: "",
        quantity: "",
        price: "",
        status: "under_use",
      });
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to create inventory item"
      );
    }
  };

  const deleteItem = async (name) => {
    try {
      setError("");

      if (MOCK_MODE) {
        setItems(items.filter((item) => item.name !== name));
        return;
      }

      const encodedName = encodeURIComponent(name);

      await api.delete(`/inventory/${encodedName}`);
      await fetchInventory();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to delete inventory item"
      );
    }
  };

  const updateStatus = async (name, status) => {
    try {
      setError("");

      if (MOCK_MODE) {
        setItems(
          items.map((item) =>
            item.name === name
              ? { ...item, status }
              : item
          )
        );
        return;
      }

      const encodedName = encodeURIComponent(name);

      await api.put(
        `/inventory/${encodedName}/status`,
        { status }
      );

      await fetchInventory();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to update inventory status"
      );
    }
  };

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
          Inventory Module
        </h1>

        {/* Error */}
        {error && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 p-4 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex mb-8 space-x-8 border-b border-gray-800">
          <button
            onClick={() => setActiveTab("inventory")}
            className={`pb-2 ${
              activeTab === "inventory"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Inventory
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

        {activeTab === "inventory" && (
          <>
            {/* Add Inventory */}
            <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl mb-8">
              <div className="flex flex-wrap gap-4">
                <input
                  value={form.name}
                  placeholder="Name"
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) =>
                    setForm({
                      ...form,
                      name: e.target.value,
                    })
                  }
                />

                <input
                  value={form.quantity}
                  placeholder="Quantity"
                  type="number"
                  min="0"
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) =>
                    setForm({
                      ...form,
                      quantity: e.target.value,
                    })
                  }
                />

                <input
                  value={form.price}
                  placeholder="Price"
                  type="number"
                  min="0"
                  step="0.01"
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) =>
                    setForm({
                      ...form,
                      price: e.target.value,
                    })
                  }
                />

                <select
                  value={form.status}
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) =>
                    setForm({
                      ...form,
                      status: e.target.value,
                    })
                  }
                >
                  <option value="under_use">
                    Under Use
                  </option>
                  <option value="ordered">
                    Ordered
                  </option>
                  <option value="consumed">
                    Consumed
                  </option>
                </select>

                <button
                  onClick={createItem}
                  className="bg-indigo-600 hover:bg-indigo-700 px-6 py-3 rounded-lg"
                >
                  Add
                </button>
              </div>
            </div>

            {/* Inventory Table */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-800 text-gray-400 text-sm uppercase">
                  <tr>
                    <th className="p-4">Name</th>
                    <th className="p-4">Units</th>
                    <th className="p-4">Price</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className="border-t border-gray-800 hover:bg-gray-800/50"
                    >
                      <td className="p-4">
                        {item.name}
                      </td>

                      <td className="p-4">
                        {item.quantity}
                      </td>

                      <td className="p-4">
                        ${item.price}
                      </td>

                      <td className="p-4 capitalize">
                        {item.status}
                      </td>

                      <td className="p-4 space-x-2">
                        <select
                          onChange={(e) =>
                            updateStatus(
                              item.name,
                              e.target.value
                            )
                          }
                          value={item.status}
                          className="bg-gray-800 p-1 rounded"
                        >
                          <option value="under_use">
                            Under Use
                          </option>
                          <option value="ordered">
                            Ordered
                          </option>
                          <option value="consumed">
                            Consumed
                          </option>
                        </select>

                        <button
                          onClick={() =>
                            fetchLogs(item.name)
                          }
                          className="bg-blue-600 px-3 py-1 rounded"
                        >
                          Logs
                        </button>

                        <button
                          onClick={() =>
                            deleteItem(item.name)
                          }
                          className="bg-red-600 px-3 py-1 rounded"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {activeTab === "logs" && (
          <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl">
            <h2 className="text-xl font-semibold mb-6">
              Logs for {selectedItem}
            </h2>

            {logs.length === 0 ? (
              <p className="text-gray-500">
                No logs found.
              </p>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className="flex justify-between border-b border-gray-800 py-3"
                >
                  <span className="capitalize">
                    {log.action}
                  </span>

                  <span>
                    {log.quantity}
                  </span>

                  <span className="text-gray-400">
                    {new Date(
                      log.timestamp
                    ).toLocaleString()}
                  </span>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}