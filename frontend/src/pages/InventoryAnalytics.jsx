import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import { MOCK_MODE } from "../config";
import LineChart from "../components/charts/LineChart";
import BarChart from "../components/charts/BarChart";
import { useRealtime } from "../realtime/RealtimeProvider";

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
  const { lastEvent } = useRealtime();
  const [error, setError] = useState("");

  const [alerts, setAlerts] = useState(null);
  const [stockout, setStockout] = useState([]);
  const [series, setSeries] = useState({
  daily_consumption: { series: [] },
  monthly_orders: { series: [] },
});

  const [settings, setSettings] = useState({
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

    if (MOCK_MODE) {
      setAlerts({
        exhausted: [{ name: "Glue", quantity: 0, status: "consumed" }],
        dead_stock: [{ name: "Packaging Film", quantity: 120, days_inactive: 44 }],
        expiry_risk: [
          { name: "Milk Powder", quantity: 30, expiry_date: "2026-08-25", days_to_expiry: 9, avg_daily_consumption: 1.8 },
        ],
      });

      setReorder([
        { name: "Steel", current_quantity: 40, on_order_quantity: 0, avg_daily_consumption: 8.2, consumed_last_window: 114.8, suggested_reorder_quantity: 74.8 },
        { name: "Plastic", current_quantity: 20, on_order_quantity: 10, avg_daily_consumption: 2.4, consumed_last_window: 33.6, suggested_reorder_quantity: 3.6 },
      ]);

      setStockout([
        { name: "Steel", avg_daily_consumption: 8.2, days_to_stockout: 4.87, predicted_stockout_date: "2026-08-21", current_quantity: 40 },
        { name: "Plastic", avg_daily_consumption: 2.4, days_to_stockout: 8.33, predicted_stockout_date: "2026-08-25", current_quantity: 20 },
        { name: "Bolts", avg_daily_consumption: 0, days_to_stockout: null, predicted_stockout_date: null, current_quantity: 600 },
      ]);

      setSeries({
  daily_consumption: {
    series: Array.from({ length: 20 }).map((_, i) => ({
      label: `2026-08-${String(i + 1).padStart(2, "0")}`,
      value: Math.max(
        0,
        Math.round(10 + Math.sin(i / 2) * 6 + (i % 3) * 2)
      ),
    })),
  },
  monthly_orders: {
    series: [
      { label: "2026-01", value: 180 },
      { label: "2026-02", value: 140 },
      { label: "2026-03", value: 220 },
      { label: "2026-04", value: 110 },
      { label: "2026-05", value: 260 },
      { label: "2026-06", value: 190 },
      { label: "2026-07", value: 300 },
      { label: "2026-08", value: 210 },
    ],
  },
});
      return;
    }

    try {
      const [a, ser] = await Promise.all([
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
    ]);

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
  useEffect(() => {
    if (
      lastEvent?.type === "analytics.updated" &&
      lastEvent?.module === "inventory"
    ) {
      fetchAll();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastEvent]);
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
  const expiryCount = alerts?.expiry_risk?.length || 0;

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
              subtitle="Total ordered quantity per month"
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
                {(alerts?.expiry_risk || []).map((x) => (
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
                {(alerts?.expiry_risk || []).length === 0 && (
                  <div className="text-gray-500 text-sm">No expiry risk detected.</div>
                )}
              </div>
            </Panel>
          </div>
        </div>

        {/* Reorder + Stockout tables */}
        <div className="grid grid-cols-12 gap-6 mt-8">
        </div>
      </div>
    </div>
  );
}