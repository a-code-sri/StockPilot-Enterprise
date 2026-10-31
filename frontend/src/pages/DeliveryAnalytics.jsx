import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";

import LineChart from "../components/charts/LineChart";
import BarChart from "../components/charts/BarChart";
import PieChart from "../components/charts/PieChart";
import HistogramChart from "../components/charts/HistogramChart";
import { useAnalyticsRefresh } from "../realtime/RealtimeProvider";
import { InsightsPanel } from "../components/ui";
import { tzOffsetMinutes } from "../lib/format";
function Panel({ title, subtitle, right, children }) {
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

function Badge({ text }) {
  return (
    <span className="text-xs px-2 py-1 rounded-lg border bg-indigo-500/10 border-indigo-500/30 text-indigo-200">
      {text}
    </span>
  );
}

export default function DeliveryAnalytics() {
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  const [settings] = useState({
    days_month: 30,
    days_year: 365,
    top_n: 10,
    ma_window_month: 7,
    ma_window_year: 30,
  });

  const extractErrorDetail = (e) =>
    e?.response?.data?.detail || e?.message || "Failed to fetch delivery analytics.";

  const fetchOverview = async () => {
    setError("");


    try {
      const res = await api.get("/analytics/delivery/overview", { params: { ...settings, tz_offset_minutes: tzOffsetMinutes() } });
      setData(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  useEffect(() => {
    fetchOverview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useAnalyticsRefresh("delivery", fetchOverview);
  // ---------- Chart transforms
  const monthMA = useMemo(() => {
    const s = data?.moving_average?.month?.series || [];
    return s.map((x) => ({ label: x.day, value: x.moving_avg }));
  }, [data]);

  const yearMA = useMemo(() => {
    const s = data?.moving_average?.year?.series || [];
    // downsample for display if huge
    const step = s.length > 120 ? Math.ceil(s.length / 120) : 1;
    return s.filter((_, i) => i % step === 0).map((x) => ({ label: x.day, value: x.moving_avg }));
  }, [data]);

  const monthTopItems = useMemo(() => {
    const items = data?.most_ordered_items?.month?.items || [];
    return items.map((x) => ({ label: x.product_name, value: x.quantity }));
  }, [data]);

  const yearTopItems = useMemo(() => {
    const items = data?.most_ordered_items?.year?.items || [];
    return items.map((x) => ({ label: x.product_name, value: x.quantity }));
  }, [data]);

  const monthStatusPie = useMemo(() => {
    const c = data?.status_distribution?.month?.consolidated || {};
    return [
      { label: "Delivered", value: c.delivered || 0 },
      { label: "Active", value: c.active || 0 },
      { label: "Cancelled", value: c.cancelled || 0 },
      { label: "Failed", value: c.failed || 0 },
      { label: "Other", value: c.other || 0 },
    ];
  }, [data]);

  const yearStatusPie = useMemo(() => {
    const c = data?.status_distribution?.year?.consolidated || {};
    return [
      { label: "Delivered", value: c.delivered || 0 },
      { label: "Active", value: c.active || 0 },
      { label: "Cancelled", value: c.cancelled || 0 },
      { label: "Failed", value: c.failed || 0 },
      { label: "Other", value: c.other || 0 },
    ];
  }, [data]);

  const monthHourHist = useMemo(() => {
    const hours = data?.peak_delivery_time_histogram?.month?.hours || [];
    // Convert to bins+counts for HistogramChart:
    // bins represent hour edges (0..24), counts per hour
    const bins = Array.from({ length: 25 }).map((_, i) => i);
    const counts = hours.map((h) => h.count);
    return { bins, counts };
  }, [data]);

  const yearHourHist = useMemo(() => {
    const hours = data?.peak_delivery_time_histogram?.year?.hours || [];
    const bins = Array.from({ length: 25 }).map((_, i) => i);
    const counts = hours.map((h) => h.count);
    return { bins, counts };
  }, [data]);

  const titleGradient =
    "bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent";

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className={`text-4xl font-bold mb-2 ${titleGradient}`}>Delivery Analytics</h1>
            <p className="text-gray-400">
              Moving averages, most ordered items, status distributions and peak delivery time.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchOverview}
              className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-xl transition"
            >
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-6 bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Error</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
        )}

        <div className="mt-8"><InsightsPanel module="delivery" /></div>

        {!data ? (
          <div className="mt-8 text-gray-500">Loading analytics…</div>
        ) : (
          <>
            {/* Moving averages */}
            <div className="grid grid-cols-12 gap-6 mt-8">
              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title="Daily Deliveries Moving Average (Last Month)"
                  subtitle={`Delivered orders • ${data.moving_average.month.days} days • window ${data.moving_average.month.window}`}
                  right={<Badge text="Month" />}
                >
                  <LineChart data={monthMA} />
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title="Daily Deliveries Moving Average (Last Year)"
                  subtitle={`Delivered orders • ${data.moving_average.year.days} days • window ${data.moving_average.year.window}`}
                  right={<Badge text="Year" />}
                >
                  <LineChart data={yearMA} />
                </Panel>
              </div>
            </div>

            {/* Most ordered items */}
            <div className="grid grid-cols-12 gap-6 mt-8">
              <div className="col-span-12 xl:col-span-6">
                <Panel title="Most Ordered Items (Month)" subtitle="Top items by quantity">
                  <BarChart data={monthTopItems} />
                  <div className="text-xs text-gray-500 mt-3">
                    Showing top {data.most_ordered_items.month.top_n}.
                  </div>
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel title="Most Ordered Items (Year)" subtitle="Top items by quantity">
                  <BarChart data={yearTopItems} />
                  <div className="text-xs text-gray-500 mt-3">
                    Showing top {data.most_ordered_items.year.top_n}.
                  </div>
                </Panel>
              </div>
            </div>

            {/* Status distribution */}
            <div className="grid grid-cols-12 gap-6 mt-8">
              <div className="col-span-12 xl:col-span-6">
                <Panel title="Order Status Distribution (Month)" subtitle="Consolidated buckets">
                  <PieChart data={monthStatusPie} centerLabel="Orders" />
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel title="Order Status Distribution (Year)" subtitle="Consolidated buckets">
                  <PieChart data={yearStatusPie} centerLabel="Orders" />
                </Panel>
              </div>
            </div>

            {/* Peak delivery time histogram */}
            <div className="grid grid-cols-12 gap-6 mt-8">
              <div className="col-span-12 xl:col-span-6">
                <Panel title="Peak Delivery Time (Month)" subtitle="Hour deliveries were completed, in your local time (rounded to the hour)">
                  <HistogramChart bins={monthHourHist.bins} counts={monthHourHist.counts} />
                  <div className="text-xs text-gray-500 mt-3">
                    Hours represent completion time of delivered orders.
                  </div>
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel title="Peak Delivery Time (Year)" subtitle="Hour deliveries were completed, in your local time (rounded to the hour)">
                  <HistogramChart bins={yearHourHist.bins} counts={yearHourHist.counts} />
                </Panel>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}