import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import { MOCK_MODE } from "../config";
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

export default function OrganizationAnalytics() {
  const [error, setError] = useState("");
  const [bins, setBins] = useState(10);
  const [data, setData] = useState(null);
  const { lastEvent } = useRealtime();

  const extractErrorDetail = (e) =>
    e?.response?.data?.detail || e?.message || "Failed to fetch organization analytics.";

  const fetchOverview = async () => {
    setError("");

    if (MOCK_MODE) {
      setData({
        total_employees: 18,
        department_share: [
          { department: "Operations", headcount: 8, percent: 44.44 },
          { department: "Warehouse", headcount: 5, percent: 27.78 },
          { department: "Finance", headcount: 3, percent: 16.67 },
          { department: "HR", headcount: 2, percent: 11.11 },
        ],
        salary_histogram: {
          bins: [30000, 40000, 50000, 60000, 70000, 80000, 90000],
          counts: [2, 5, 4, 3, 2, 2],
          min: 32000,
          max: 92000,
          avg: 58500,
          median: 56000,
        },
        top_executive: {
          employee_id: "E100",
          name: "Aarav Mehta",
          salary: 92000,
          job_role: "Plant Manager",
          departments: ["Operations"],
        },
      });
      return;
    }

    try {
      const res = await api.get("/analytics/organization/overview", {
        params: { histogram_bins: bins },
      });
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
      lastEvent?.module === "organization"
    ) {
      fetchOverview();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastEvent]);
 const pieData = useMemo(() => {
  const rows = data?.department_share || [];

  return rows.map((r) => ({
    label: r.label,
    value: r.value,
  }));
}, [data]);

const histogramData = useMemo(() => {
  const series = data?.salary_histogram?.series || [];

  return {
    bins: series.map((bucket) => bucket.bin_start),
    counts: series.map((bucket) => bucket.count),
  };
}, [data]);
  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
              Organization Analytics
            </h1>
            <p className="text-gray-400">
              Department share, salary distribution and top executive insight.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-2"
              value={bins}
              onChange={(e) => setBins(Number(e.target.value))}
            >
              <option value={6}>6 bins</option>
              <option value={10}>10 bins</option>
              <option value={14}>14 bins</option>
            </select>

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
            <div className="grid grid-cols-12 gap-6 mt-8">
              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title="Department Share"
                  subtitle="Headcount distribution by department"
                  right={<Badge text={`Total: ${data.total_employees}`} />}
                >
                  <PieChart
                    data={pieData}
                    centerLabel="Employees"
                    centerValue={data.total_employees}
                  />
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title="Top Executive"
                  subtitle="Highest salary employee"
                >
                  {data.top_executive ? (
                    <div className="bg-gray-950/40 border border-gray-800 rounded-2xl p-6">
                      <div className="flex items-center justify-between gap-4">
                        <div>
                          <div className="text-xl font-bold text-indigo-200">
                            {data.top_executive.name}
                          </div>
                          <div className="text-sm text-gray-400 mt-1">
                            {data.top_executive.job_role} •{" "}
                            <span className="font-mono">{data.top_executive.employee_id}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-gray-400 uppercase">Salary</div>
                          <div className="text-2xl font-bold text-emerald-300">
                            ${Math.round(data.top_executive.salary)}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-3">
                        <span className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200">
                          {data.top_executive.employee_id}
                        </span>

                        <span className="text-xs px-2 py-1 rounded-lg bg-gray-800 border border-gray-700 text-gray-300">
                          {data.top_executive.subordinates ?? 0} subordinates
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-500 text-sm">No executive found.</div>
                  )}
                </Panel>
              </div>
            </div>

            <div className="grid grid-cols-12 gap-6 mt-8">
              <div className="col-span-12">
                <Panel
                  title="Salary Distribution (Histogram)"
                  subtitle="Employee salary spread"
                  right={
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span>
                        Min:{" "}
                        <span className="text-gray-200">
                          {data.salary_stats?.min ?? "-"}
                        </span>
                      </span>

                      <span>
                        Max:{" "}
                        <span className="text-gray-200">
                          {data.salary_stats?.max ?? "-"}
                        </span>
                      </span>

                      <span>
                        Avg:{" "}
                        <span className="text-gray-200">
                          {data.salary_stats?.avg ?? "-"}
                        </span>
                      </span>

                      <span>
                        Median:{" "}
                        <span className="text-gray-200">
                          {data.salary_stats?.median ?? "-"}
                        </span>
                      </span>
                    </div>
                  }
                >
                  <HistogramChart
                    bins={histogramData.bins}
                    counts={histogramData.counts}
                  />
                </Panel>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}