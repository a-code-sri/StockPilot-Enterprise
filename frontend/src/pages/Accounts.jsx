import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import { MOCK_MODE } from "../config";

export default function Accounts() {

  const [activeTab, setActiveTab] = useState("transactions");
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);

  const [form, setForm] = useState({
    amount: "",
    transaction_type: "credit",
    source_target: "",
    category: "",
    remarks: ""
  });

  useEffect(() => {
    fetchTransactions();
    fetchSummary();
  }, []);

  const fetchTransactions = async () => {
    if (MOCK_MODE) {
      setTransactions([
        {
          id: 1,
          amount: 5000,
          transaction_type: "credit",
          source_target: "Client A",
          category: "delivery",
          remarks: "Bulk order payment",
          date: "2026-08-01"
        },
        {
          id: 2,
          amount: 2000,
          transaction_type: "debit",
          source_target: "Raw Material Supplier",
          category: "inventory",
          remarks: "Steel purchase",
          date: "2026-08-02"
        }
      ]);
    } else {
      const res = await api.get("/accounts");
      setTransactions(res.data);
    }
  };

  const fetchSummary = async () => {
    if (MOCK_MODE) {
      setSummary({
        current_balance: 3000,
        total_credit: 5000,
        total_debit: 2000,
        last_30_days_net: 2500
      });
    } else {
      const res = await api.get("/accounts/summary");
      setSummary(res.data);
    }
  };

  const createTransaction = async () => {
    if (MOCK_MODE) {
      setTransactions([
        {
          id: transactions.length + 1,
          ...form,
          date: new Date().toISOString().split("T")[0]
        },
        ...transactions
      ]);
      return;
    }

    await api.post("/accounts", {
      ...form,
      amount: Number(form.amount)
    });

    fetchTransactions();
    fetchSummary();
  };

  const deleteTransaction = async (id) => {
    if (MOCK_MODE) {
      setTransactions(transactions.filter(t => t.id !== id));
      return;
    }

    await api.delete(`/accounts/${id}`);
    fetchTransactions();
    fetchSummary();
  };

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">

        <h1 className="text-4xl font-bold mb-8 bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
          Accounts Module
        </h1>

        {/* Tabs */}
        <div className="flex mb-8 space-x-8 border-b border-gray-800">
          <button
            onClick={() => setActiveTab("transactions")}
            className={`pb-2 ${activeTab === "transactions"
              ? "border-b-2 border-indigo-500 text-indigo-400"
              : "text-gray-400"
              }`}
          >
            Transactions
          </button>

          <button
            onClick={() => setActiveTab("summary")}
            className={`pb-2 ${activeTab === "summary"
              ? "border-b-2 border-indigo-500 text-indigo-400"
              : "text-gray-400"
              }`}
          >
            Overall
          </button>
        </div>

        {/* TRANSACTIONS TAB */}
        {activeTab === "transactions" && (
          <>
            {/* Add Transaction */}
            <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl mb-8">
              <div className="flex flex-wrap gap-4">

                <input
                  type="number"
                  placeholder="Amount"
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) => setForm({ ...form, amount: e.target.value })}
                />

                <select
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) =>
                    setForm({ ...form, transaction_type: e.target.value })
                  }
                >
                  <option value="credit">Credit</option>
                  <option value="debit">Debit</option>
                </select>

                <input
                  placeholder="Source / Target"
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) =>
                    setForm({ ...form, source_target: e.target.value })
                  }
                />

                <input
                  placeholder="Category (Module)"
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) =>
                    setForm({ ...form, category: e.target.value })
                  }
                />

                <input
                  placeholder="Remarks"
                  className="bg-gray-800 p-3 rounded"
                  onChange={(e) =>
                    setForm({ ...form, remarks: e.target.value })
                  }
                />

                <button
                  onClick={createTransaction}
                  className="bg-indigo-600 hover:bg-indigo-700 px-6 py-3 rounded-lg"
                >
                  Add
                </button>
              </div>
            </div>

            {/* Transactions Table */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-800 text-gray-400 text-sm uppercase">
                  <tr>
                    <th className="p-4">Date</th>
                    <th className="p-4">Type</th>
                    <th className="p-4">Amount</th>
                    <th className="p-4">Source / Target</th>
                    <th className="p-4">Category</th>
                    <th className="p-4">Remarks</th>
                    <th className="p-4">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map(t => (
                    <tr key={t.id} className="border-t border-gray-800 hover:bg-gray-800/50">
                      <td className="p-4">{t.date}</td>
                      <td className={`p-4 capitalize ${
                        t.transaction_type === "credit"
                          ? "text-green-400"
                          : "text-red-400"
                      }`}>
                        {t.transaction_type}
                      </td>
                      <td className="p-4">${t.amount}</td>
                      <td className="p-4">{t.source_target}</td>
                      <td className="p-4">{t.category}</td>
                      <td className="p-4">{t.remarks}</td>
                      <td className="p-4">
                        <button
                          onClick={() => deleteTransaction(t.id)}
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

        {/* SUMMARY TAB */}
        {activeTab === "summary" && summary && (
          <div className="grid grid-cols-4 gap-8">

            <Card title="Current Balance" value={`$${summary.current_balance}`} highlight />

            <Card title="Total Credit" value={`$${summary.total_credit}`} green />

            <Card title="Total Debit" value={`$${summary.total_debit}`} red />

            <Card title="Last 30 Days Net" value={`$${summary.last_30_days_net}`} />

          </div>
        )}
      </div>
    </div>
  );
}

function Card({ title, value, highlight, green, red }) {
  return (
    <div className="bg-gray-900 border border-gray-800 p-8 rounded-2xl shadow-lg">
      <h3 className="text-gray-400 text-sm uppercase tracking-wide mb-4">
        {title}
      </h3>
      <p className={`text-3xl font-bold ${
        highlight ? "text-indigo-400" :
        green ? "text-green-400" :
        red ? "text-red-400" :
        "text-gray-200"
      }`}>
        {value}
      </p>
    </div>
  );
}