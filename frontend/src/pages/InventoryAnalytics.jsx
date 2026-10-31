import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import LineChart from "../components/charts/LineChart";
import BarChart from "../components/charts/BarChart";
import { useAnalyticsRefresh } from "../realtime/RealtimeProvider";
import { InsightsPanel } from "../components/ui";

function Panel({ title, subtitle, children, right }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
      <div className="p-5 border-b border-gray-800 flex items-start justify-between gap-4">
        <div>
          <div className="font-semibold">{title}</div>
          {subtitle && <div className="text-xs text-gray-400 mt-1">{subtitle}</div>}
        </div>
        {right}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Badge({ text, tone = "indigo" }) {
  const map = {
    indigo: "bg-indigo-500/10 border-indigo-500/30 text-indigo-200",
    red: "bg-red-500/10 border-red-500/30 text-red-200",
    amber: "bg-yellow-500/10 border-yellow-500/30 text-yellow-200",
    emerald: "bg-emerald-500/10 border-emerald-500/30 text-emerald-200",
  };
  return (
    <span className={`text-xs px-2 py-1 rounded-lg border ${map[tone] || map.indigo}`}>
      {text}
    </span>
  );
}

export default function InventoryAnalytics() {
  const [error, setError] = useState("");

  const [alerts, setAlerts] = useState(null);
  const [stockout, setStockout] = useState([]);
  const [reorder, setReorder] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [series, setSeries] = useState({
  daily_consumption: { series: [] },
  monthly_orders: { series: [] },
});

  const [settings] = useState({
    dead_days: 30,
    expiry_days: 14,
    consumption_days: 14,
    coverage_days: 14,
    chart_days: 30,
    order_months: 12,
  });

  const extractErrorDetail = (e) =>
    e?.response?.data?.detail || e?.message || "Failed to fetch analytics.";

  const fetchAll = async () => {
    setError("");


    try {
      const [a, ser, so, ro, an] = await Promise.all([
      api.get("/analytics/inventory/alerts", {
        params: {
          dead_days: settings.dead_days,
          expiry_days: settings.expiry_days,
          consumption_days: settings.consumption_days,
        },
      }),
      api.get("/analytics/inventory/series", {
        params: {
          consumption_days: settings.chart_days,
          order_months: settings.order_months,
        },
      }),
      api.get("/analytics/inventory/stockout-predictions", {
        params: { consumption_days: settings.consumption_days },
      }),
      api.get("/analytics/inventory/reorder-suggestions", {
        params: { consumption_days: settings.consumption_days, coverage_days: settings.coverage_days },
      }),
      api.get("/analytics/inventory/anomalies"),
    ]);
    setStockout(so.data.filter((x) => x.days_to_stockout !== null).slice(0, 10));
    setReorder(ro.data.filter((x) => x.suggested_reorder_quantity > 0).slice(0, 10));
    setAnomalies(an.data.anomalies);

    setAlerts(a.data);
    setSeries(ser.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  useEffect(() => {
    fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useAnalyticsRefresh("inventory", fetchAll);
  const consumptionForChart = useMemo(
    () =>
      (series.daily_consumption?.series || []).map((d) => ({
        label: d.label,
        value: d.value,
      })),
    [series]
  );

  const ordersForChart = useMemo(
    () =>
      (series.monthly_orders?.series || []).map((m) => ({
        label: m.label,
        value: m.value,
      })),
    [series]
  );

  const exhaustedCount = alerts?.exhausted?.length || 0;
  const deadCount = alerts?.dead_stock?.length || 0;
  const expiryCount = alerts?.near_expiry?.length || 0;

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
              Inventory Analytics
            </h1>
            <p className="text-gray-400">
              Dead stock, reorder suggestions, stockout prediction and trend charts.
            </p>
          </div>

          <button
            onClick={fetchAll}
            className="bg-gray-900 border border-gray-800 hover:border-indigo-500/60 px-4 py-2 rounded-xl transition"
          >
            Refresh
          </button>
        </div>

        {error && (
          <div className="mt-6 bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Error</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
        )}

        <div className="mt-8"><InsightsPanel module="inventory" /></div>

        {/* top counters */}
        <div className="grid grid-cols-12 gap-6 mt-8">
          <div className="col-span-12 lg:col-span-4 bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <div className="text-xs text-gray-400 uppercase">Exhausted Alerts</div>
            <div className="mt-3 text-3xl font-bold text-red-300">{exhaustedCount}</div>
          </div>
          <div className="col-span-12 lg:col-span-4 bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <div className="text-xs text-gray-400 uppercase">Dead Stock Alerts</div>
            <div className="mt-3 text-3xl font-bold text-amber-300">{deadCount}</div>
          </div>
          <div className="col-span-12 lg:col-span-4 bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <div className="text-xs text-gray-400 uppercase">Expiry Risk Alerts</div>
            <div className="mt-3 text-3xl font-bold text-purple-300">{expiryCount}</div>
          </div>
        </div>

        {/* charts */}
        <div className="grid grid-cols-12 gap-6 mt-8">
          <div className="col-span-12 xl:col-span-7">
            <Panel
              title="Consumption (Daily)"
              subtitle="Total consumed/delivered quantity per day"
              right={<Badge text={`${settings.chart_days} days`} tone="indigo" />}
            >
              <LineChart data={consumptionForChart} />
            </Panel>
          </div>

          <div className="col-span-12 xl:col-span-5">
            <Panel
              title="Orders (Monthly)"
              subtitle="Purchase orders placed per month"
              right={<Badge text={`${settings.order_months} months`} tone="purple" />}
            >
              <BarChart data={ordersForChart} />
            </Panel>
          </div>
        </div>

        {/* Alerts breakdown */}
        <div className="grid grid-cols-12 gap-6 mt-8">
          <div className="col-span-12 xl:col-span-4">
            <Panel title="Exhausted Items" subtitle="Quantity is 0">
              <div className="space-y-3">
                {(alerts?.exhausted || []).map((x) => (
                  <div key={x.name} className="bg-gray-950 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
                    <div className="font-semibold">{x.name}</div>
                    <Badge text="Exhausted" tone="red" />
                  </div>
                ))}
                {(alerts?.exhausted || []).length === 0 && (
                  <div className="text-gray-500 text-sm">No exhausted items.</div>
                )}
              </div>
            </Panel>
          </div>

          <div className="col-span-12 xl:col-span-4">
            <Panel title="Dead Stock" subtitle="No movement for N days">
              <div className="space-y-3">
                {(alerts?.dead_stock || []).map((x) => (
                  <div key={x.name} className="bg-gray-950 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
                    <div>
                      <div className="font-semibold">{x.name}</div>
                      <div className="text-xs text-gray-500 mt-1">{x.days_inactive} days inactive</div>
                    </div>
                    <Badge text="Dead stock" tone="amber" />
                  </div>
                ))}
                {(alerts?.dead_stock || []).length === 0 && (
                  <div className="text-gray-500 text-sm">No dead stock detected.</div>
                )}
              </div>
            </Panel>
          </div>

          <div className="col-span-12 xl:col-span-4">
            <Panel title="Expiry Risk" subtitle="Expiring soon or consumption too slow">
              <div className="space-y-3">
                {(alerts?.near_expiry || []).map((x) => (
                  <div key={x.name} className="bg-gray-950 border border-gray-800 rounded-xl p-4">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold">{x.name}</div>
                      <Badge text={`${x.days_to_expiry} days`} tone="purple" />
                    </div>
                    <div className="text-xs text-gray-500 mt-2">
                      Expiry: {x.expiry_date} • Avg daily consumption: {x.avg_daily_consumption}
                    </div>
                  </div>
                ))}
                {(alerts?.near_expiry || []).length === 0 && (
                  <div className="text-gray-500 text-sm">No expiry risk detected.</div>
                )}
              </div>
            </Panel>
          </div>
        </div>

        {/* Reorder + Stockout tables */}
        <div className="grid grid-cols-12 gap-6 mt-8">
          <div className="col-span-12 xl:col-span-6">
            <Panel title="Reorder suggestions" subtitle={`Units needed to cover the next ${settings.coverage_days} days`}>
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-400 uppercase text-left">
                  <tr><th className="pb-2">Item</th><th className="pb-2 text-right">Stock</th><th className="pb-2 text-right">On order</th><th className="pb-2 text-right">Per day</th><th className="pb-2 text-right">Order</th></tr>
                </thead>
                <tbody>
                  {reorder.map((r) => (
                    <tr key={r.id} className="border-t border-gray-800">
                      <td className="py-2">{r.name}</td>
                      <td className="py-2 text-right">{r.current_quantity}</td>
                      <td className="py-2 text-right">{r.on_order_quantity}</td>
                      <td className="py-2 text-right">{r.avg_daily_consumption}</td>
                      <td className="py-2 text-right font-semibold text-indigo-300">{Math.ceil(r.suggested_reorder_quantity)}</td>
                    </tr>
                  ))}
                  {reorder.length === 0 && <tr><td colSpan={5} className="py-3 text-gray-500">Nothing needs reordering.</td></tr>}
                </tbody>
              </table>
            </Panel>
          </div>
          <div className="col-span-12 xl:col-span-6">
            <Panel title="Stock-out forecast" subtitle="At the current consumption rate">
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-400 uppercase text-left">
                  <tr><th className="pb-2">Item</th><th className="pb-2 text-right">Stock</th><th className="pb-2 text-right">Days left</th><th className="pb-2 text-right">Runs out</th></tr>
                </thead>
                <tbody>
                  {stockout.map((r) => (
                    <tr key={r.id} className="border-t border-gray-800">
                      <td className="py-2">{r.name}</td>
                      <td className="py-2 text-right">{r.current_quantity}</td>
                      <td className={`py-2 text-right ${r.days_to_stockout < 7 ? "text-red-300" : ""}`}>{r.days_to_stockout}</td>
                      <td className="py-2 text-right text-gray-400">{r.predicted_stockout_date}</td>
                    </tr>
                  ))}
                  {stockout.length === 0 && <tr><td colSpan={4} className="py-3 text-gray-500">No consumption in the window, so no forecast.</td></tr>}
                </tbody>
              </table>
            </Panel>
          </div>
          <div className="col-span-12">
            <Panel title="Unusual consumption" subtitle="Days where an item was used far more than usual (robust z-score)">
              <ul className="space-y-2 text-sm">
                {anomalies.map((a) => (
                  <li key={`${a.item_id}-${a.day}`} className="flex justify-between gap-4 border-b border-gray-800 pb-2">
                    <span><span className="font-medium">{a.name}</span> <span className="text-gray-400">· {a.day}</span>
                      <span className="block text-xs text-gray-500">{a.reason}</span></span>
                    <Badge text={`score ${a.score}`} tone="amber" />
                  </li>
                ))}
                {anomalies.length === 0 && <li className="text-gray-500">No unusual consumption detected.</li>}
              </ul>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}