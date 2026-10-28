import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import { MOCK_MODE } from "../config";

import LineChart from "../components/charts/LineChart";
import BarChart from "../components/charts/BarChart";
import PieChart from "../components/charts/PieChart";
import HistogramChart from "../components/charts/HistogramChart";
import { useRealtime } from "../realtime/RealtimeProvider";
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
  const { lastEvent } = useRealtime();

  const [settings, setSettings] = useState({
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

    if (MOCK_MODE) {
      const mkSeries = (days, window) =>
        Array.from({ length: Math.min(days, 60) }).map((_, i) => {
          const base = days > 60 ? 80 : 12;
          const v = Math.max(0, Math.round(base + Math.sin(i / 3) * (base / 3) + (i % 5)));
          return {
            day: `2026-08-${String((i % 30) + 1).padStart(2, "0")}`,
            count: v,
            moving_avg: Math.max(0, v - 2),
          };
        });

      setData({
        moving_average: {
          month: { days: settings.days_month, window: settings.ma_window_month, series: mkSeries(settings.days_month, settings.ma_window_month) },
          year: { days: settings.days_year, window: settings.ma_window_year, series: mkSeries(settings.days_year, settings.ma_window_year) },
        },
        most_ordered_items: {
          month: {
            days: settings.days_month,
            top_n: settings.top_n,
            items: [
              { product_name: "Widget A", quantity: 340 },
              { product_name: "Widget B", quantity: 280 },
              { product_name: "Tape", quantity: 210 },
              { product_name: "Packaging", quantity: 190 },
            ],
          },
          year: {
            days: settings.days_year,
            top_n: settings.top_n,
            items: [
              { product_name: "Widget A", quantity: 4200 },
              { product_name: "Widget B", quantity: 3600 },
              { product_name: "Packaging", quantity: 2500 },
              { product_name: "Tape", quantity: 2200 },
              { product_name: "Spare Part", quantity: 900 },
            ],
          },
        },
        status_distribution: {
          month: {
            days: settings.days_month,
            consolidated: { active: 48, delivered: 320, cancelled: 14, failed: 6, other: 2 },
            raw: {},
          },
          year: {
            days: settings.days_year,
            consolidated: { active: 60, delivered: 4020, cancelled: 210, failed: 90, other: 14 },
            raw: {},
          },
        },
        peak_delivery_time_histogram: {
          month: {
            days: settings.days_month,
            hours: Array.from({ length: 24 }).map((_, h) => ({
              hour: h,
              count: h >= 10 && h <= 18 ? Math.round(8 + (18 - Math.abs(14 - h)) * 3) : Math.round(2 + (h % 3)),
            })),
          },
          year: {
            days: settings.days_year,
            hours: Array.from({ length: 24 }).map((_, h) => ({
              hour: h,
              count: h >= 10 && h <= 18 ? Math.round(40 + (18 - Math.abs(14 - h)) * 15) : Math.round(10 + (h % 5)),
            })),
          },
        },
      });
      return;
    }

    try {
      const res = await api.get("/analytics/delivery/overview", { params: settings });
      setData(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  useEffect(() => {
    fetchOverview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (
      lastEvent?.type === "analytics.updated" &&
      lastEvent?.module === "delivery"
    ) {
      fetchOverview();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastEvent]);
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
                <Panel title="Peak Delivery Time (Month)" subtitle="Delivered completion hour (0–23)">
                  <HistogramChart bins={monthHourHist.bins} counts={monthHourHist.counts} />
                  <div className="text-xs text-gray-500 mt-3">
                    Hours represent completion time of delivered orders.
                  </div>
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel title="Peak Delivery Time (Year)" subtitle="Delivered completion hour (0–23)">
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