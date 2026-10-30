import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Sidebar from "../components/Sidebar";
import api from "../api";
import { useAuth } from "../context/AuthContext";

import LineChart from "../components/charts/LineChart";
import DonutChart from "../components/charts/DonutChart";
import PieChart from "../components/charts/PieChart";

function Panel({ title, subtitle, action, children }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
      <div className="p-5 border-b border-gray-800 flex items-start justify-between gap-4">
        <div>
          <div className="font-semibold">{title}</div>

          {subtitle && (
            <div className="text-xs text-gray-400 mt-1">
              {subtitle}
            </div>
          )}
        </div>

        {action}
      </div>

      <div className="p-5">{children}</div>
    </div>
  );
}

function StatCard({ title, value, tone = "indigo" }) {
  const tones = {
    indigo: "text-indigo-300",
    red: "text-red-300",
    amber: "text-yellow-300",
    purple: "text-purple-300",
    emerald: "text-emerald-300",
  };

  return (
    <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl">
      <div className="text-xs text-gray-400 uppercase">
        {title}
      </div>

      <div
        className={`mt-3 text-3xl font-bold ${
          tones[tone] || tones.indigo
        }`}
      >
        {value}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { can } = useAuth();
  const navigate = useNavigate();

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // ------------------------------------------------------------
  // Inventory snapshot
  // ------------------------------------------------------------

  const [invSeries, setInvSeries] = useState([]);

  const [invAlerts, setInvAlerts] = useState({
    exhausted: 0,
    dead_stock: 0,
    expiry_risk: 0,
  });

  // ------------------------------------------------------------
  // Accounts snapshot
  // ------------------------------------------------------------

  const [acctOverview, setAcctOverview] = useState({
    income: 0,
    expenses: 0,
    net: 0,
  });

  // ------------------------------------------------------------
  // Organization snapshot
  // ------------------------------------------------------------

  const [orgOverview, setOrgOverview] = useState(null);

  // ------------------------------------------------------------
  // Delivery snapshot
  // ------------------------------------------------------------

  const [deliverySeries, setDeliverySeries] = useState([]);

  // ------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------

  const extractErrorDetail = (e) =>
    e?.response?.data?.detail ||
    e?.message ||
    "Failed to load dashboard.";

  // ------------------------------------------------------------
  // Fetch dashboard snapshots
  // ------------------------------------------------------------

  const fetchSnapshots = async () => {
    setError("");
    setLoading(true);

    // Only call endpoints this user may read; a missing permission (or one
    // failing module) must not blank the whole dashboard.
    const failures = [];
    const get = (permission, url, params) =>
      can(permission)
        ? api.get(url, { params }).catch((e) => {
            failures.push(extractErrorDetail(e));
            return null;
          })
        : Promise.resolve(null);

    try {
      const [invSeriesRes, invAlertsRes, accountsRes, orgRes, deliveryRes] = await Promise.all([
        get("inventory.read", "/analytics/inventory/series", { consumption_days: 14, order_months: 6 }),
        get("inventory.read", "/analytics/inventory/alerts", { dead_days: 30, expiry_days: 14, consumption_days: 14 }),
        get("accounts.read", "/analytics/accounts/overview", { days: 30, top_n: 5 }),
        get("organization.read", "/analytics/organization/overview", { histogram_bins: 10 }),
        get("delivery.read", "/analytics/delivery/overview"),
      ]);
      if (failures.length) setError(failures[0]);

      // ----------------------------------------------------------
      // Inventory
      //
      // Backend:
      // {
      //   daily_consumption: {
      //      days,
      //      series: [{ label, value }]
      //   },
      //   monthly_orders: ...
      // }
      // ----------------------------------------------------------

      const dailyConsumption =
        invSeriesRes?.data?.daily_consumption?.series || [];

      setInvSeries(
        dailyConsumption.map((item) => ({
          label: item.label,
          value: Number(item.value || 0),
        }))
      );

      // ----------------------------------------------------------
      // Inventory alerts (counts; the analytics page shows the item lists)
      // ----------------------------------------------------------

      const alerts = invAlertsRes?.data || {};

      setInvAlerts({
        exhausted: Number(alerts.exhausted_count || 0),
        dead_stock: Number(alerts.dead_stock_count || 0),
        expiry_risk: Number(alerts.near_expiry_count || 0),
      });

      // ----------------------------------------------------------
      // Accounts
      //
      // Backend overview contains:
      // income_vs_expenses: {
      //   income,
      //   expenses,
      //   net
      // }
      // ----------------------------------------------------------

      const incomeExpenses =
        accountsRes?.data?.income_vs_expenses || {};

      setAcctOverview({
        income: Number(incomeExpenses.income || 0),
        expenses: Number(incomeExpenses.expenses || 0),
        net: Number(incomeExpenses.net || 0),
      });

      // ----------------------------------------------------------
      // Organization
      // ----------------------------------------------------------

      setOrgOverview(orgRes?.data || null);

      // ----------------------------------------------------------
      // Delivery
      //
      // Use the monthly moving-average series.
      // ----------------------------------------------------------

      const monthlyMovingAverage =
        deliveryRes?.data?.moving_average?.month?.series || [];

      setDeliverySeries(
        monthlyMovingAverage.map((item) => ({
          label: item.day,
          value: Number(item.moving_avg || 0),
        }))
      );
    } catch (e) {
      setError(extractErrorDetail(e));
    } finally {
      setLoading(false);
    }
  };

  // ------------------------------------------------------------
  // Initial load
  // ------------------------------------------------------------

  useEffect(() => {
    fetchSnapshots();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ------------------------------------------------------------
  // Derived inventory alert counts
  // ------------------------------------------------------------

  const exhaustedCount = invAlerts.exhausted || 0;
  const deadCount = invAlerts.dead_stock || 0;
  const expiryCount = invAlerts.expiry_risk || 0;

  const totalInventoryAlerts =
    exhaustedCount + deadCount + expiryCount;

  // ------------------------------------------------------------
  // Organization Pie Chart
  //
  // Backend:
  // department_share: [
  //   { label, value, pct }
  // ]
  // ------------------------------------------------------------

  const orgPieData = useMemo(() => {
    return (orgOverview?.department_share || []).map((item) => ({
      label: item.label,
      value: Number(item.value || 0),
    }));
  }, [orgOverview]);

  // ------------------------------------------------------------
  // Render
  // ------------------------------------------------------------

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        {/* -------------------------------------------------- */}
        {/* Header */}
        {/* -------------------------------------------------- */}

        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
              Dashboard Overview
            </h1>

            <p className="text-gray-400">
              Default analytics snapshot (Inventory, Accounts,
              Organization, Delivery).
            </p>
          </div>

          <button
            onClick={fetchSnapshots}
            disabled={loading}
            className="bg-gray-900 border border-gray-800 hover:border-indigo-500/60 px-4 py-2 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {/* -------------------------------------------------- */}
        {/* Error */}
        {/* -------------------------------------------------- */}

        {error && (
          <div className="mt-6 bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Error</div>

            <div className="text-sm mt-1">
              {error}
            </div>
          </div>
        )}

        {/* -------------------------------------------------- */}
        {/* Inventory Alert Cards */}
        {/* -------------------------------------------------- */}

        <div className="grid grid-cols-12 gap-6 mt-8">
          <div className="col-span-12 md:col-span-6 xl:col-span-3">
            <StatCard
              title="Inventory Alerts"
              value={totalInventoryAlerts}
              tone="indigo"
            />
          </div>

          <div className="col-span-12 md:col-span-6 xl:col-span-3">
            <StatCard
              title="Exhausted / Reorder"
              value={exhaustedCount}
              tone="red"
            />
          </div>

          <div className="col-span-12 md:col-span-6 xl:col-span-3">
            <StatCard
              title="Dead Stock"
              value={deadCount}
              tone="amber"
            />
          </div>

          <div className="col-span-12 md:col-span-6 xl:col-span-3">
            <StatCard
              title="Expiry Risk"
              value={expiryCount}
              tone="purple"
            />
          </div>
        </div>

        {/* -------------------------------------------------- */}
        {/* Row 1: Inventory + Accounts */}
        {/* -------------------------------------------------- */}

        <div className="grid grid-cols-12 gap-6 mt-8">
          {/* Inventory */}
          <div className="col-span-12 xl:col-span-7">
            <Panel
              title="Inventory Consumption (Last 14 days)"
              subtitle="Daily consumed/delivered quantity"
              action={
                <button
                  onClick={() =>
                    navigate("/analytics/inventory")
                  }
                  className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-xl transition"
                >
                  View Inventory Analytics
                </button>
              }
            >
              <LineChart data={invSeries} />
            </Panel>
          </div>

          {/* Accounts */}
          <div className="col-span-12 xl:col-span-5">
            <Panel
              title="Accounts (Last 30 days)"
              subtitle="Income vs expenses snapshot"
              action={
                <button
                  onClick={() =>
                    navigate("/analytics/accounts")
                  }
                  className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-xl transition"
                >
                  View Accounts Analytics
                </button>
              }
            >
              <DonutChart
                income={acctOverview.income}
                expenses={acctOverview.expenses}
              />

              <div className="mt-4 text-center text-sm text-gray-400">
                Net:
                <span className="ml-2 text-emerald-300 font-semibold">
                  {acctOverview.net.toLocaleString()}
                </span>
              </div>
            </Panel>
          </div>
        </div>

        {/* -------------------------------------------------- */}
        {/* Row 2: Organization + Top Executive */}
        {/* -------------------------------------------------- */}

        <div className="grid grid-cols-12 gap-6 mt-8">
          {/* Organization */}
          <div className="col-span-12 xl:col-span-7">
            <Panel
              title="Organization (Department Share)"
              subtitle="Headcount distribution"
              action={
                <button
                  onClick={() =>
                    navigate("/analytics/organization")
                  }
                  className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-xl transition"
                >
                  View Organization Analytics
                </button>
              }
            >
              <PieChart
                data={orgPieData}
                size={220}
                thickness={22}
                centerLabel="Employees"
                centerValue={
                  orgOverview?.total_employees ?? ""
                }
              />
            </Panel>
          </div>

          {/* Top Executive */}
          <div className="col-span-12 xl:col-span-5">
            <Panel
              title="Top Executive"
              subtitle="Highest salary"
              action={
                <button
                  onClick={() =>
                    navigate("/analytics/organization")
                  }
                  className="bg-gray-900 border border-gray-800 hover:border-indigo-500/60 px-4 py-2 rounded-xl transition"
                >
                  Details →
                </button>
              }
            >
              {orgOverview?.top_executive ? (
                <div className="bg-gray-950/40 border border-gray-800 rounded-2xl p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-lg font-bold text-indigo-200">
                        {orgOverview.top_executive.name}
                      </div>

                      <div className="text-xs text-gray-400 mt-1">
                        {orgOverview.top_executive.job_role}{" "}
                        •{" "}
                        <span className="font-mono">
                          {
                            orgOverview.top_executive
                              .employee_id
                          }
                        </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-xs text-gray-400 uppercase">
                        Salary
                      </div>

                      <div className="text-2xl font-bold text-emerald-300">
                        $
                        {Math.round(
                          Number(
                            orgOverview.top_executive.salary || 0
                          )
                        ).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {(
                      orgOverview.top_executive
                        .departments || []
                    ).map((department) => (
                      <span
                        key={department}
                        className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200"
                      >
                        {department}
                      </span>
                    ))}
                  </div>

                  <div className="mt-4 text-xs text-gray-500">
                    Salary stats: min{" "}
                    {orgOverview.salary_stats?.min ?? "-"}{" "}
                    • max{" "}
                    {orgOverview.salary_stats?.max ?? "-"}{" "}
                    • avg{" "}
                    {orgOverview.salary_stats?.avg ?? "-"}{" "}
                    • median{" "}
                    {orgOverview.salary_stats?.median ?? "-"}
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 text-sm">
                  No executive found.
                </div>
              )}
            </Panel>
          </div>
        </div>

        {/* -------------------------------------------------- */}
        {/* Row 3: Delivery */}
        {/* -------------------------------------------------- */}

        <div className="grid grid-cols-12 gap-6 mt-8">
          <div className="col-span-12">
            <Panel
              title="Delivery Moving Average (Last Month)"
              subtitle="Delivered orders moving average"
              action={
                <button
                  onClick={() =>
                    navigate("/analytics/delivery")
                  }
                  className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-xl transition"
                >
                  View Delivery Analytics
                </button>
              }
            >
              <LineChart data={deliverySeries} />
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}