import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import DonutChart from "../components/charts/DonutChart";
import { useAnalyticsRefresh } from "../realtime/RealtimeProvider";
import { InsightsPanel } from "../components/ui";
import { money as formatMoney } from "../lib/format";

function Panel({ title, subtitle, right, children }) {
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

        {right}
      </div>

      <div className="p-5">
        {children}
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  tone = "indigo",
  sub,
}) {
  const tones = {
    indigo: "text-indigo-300",
    emerald: "text-emerald-300",
    red: "text-red-300",
    purple: "text-purple-300",
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
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

      {sub && (
        <div className="text-xs text-gray-500 mt-2">
          {sub}
        </div>
      )}
    </div>
  );
}

function DistributionBars({ rows = [], tone = "indigo" }) {
  const max = Math.max(
    ...rows.map((r) => Number(r.amount || 0)),
    1
  );

  const barColor =
    tone === "emerald"
      ? "from-emerald-400/70 to-emerald-400/20"
      : "from-indigo-400/70 to-indigo-400/20";

  return (
    <div className="space-y-3">
      {rows.slice(0, 8).map((r) => {
        const amount = Number(r.amount || 0);
        const pct = (amount / max) * 100;

        return (
          <div
            key={r.category}
            className="bg-gray-950/40 border border-gray-800 rounded-xl p-4"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="font-semibold text-gray-200">
                {r.category}
              </div>

              <div className="text-sm text-gray-300">
                ${Math.round(amount).toLocaleString()}
              </div>
            </div>

            <div className="mt-3 h-2 rounded-full bg-gray-800 overflow-hidden">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${barColor}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}

      {rows.length === 0 && (
        <div className="text-gray-500 text-sm">
          No data.
        </div>
      )}
    </div>
  );
}

function RankingList({
  rows,
  labelKey,
  valueKey,
  tone,
}) {
  const pill =
    tone === "emerald"
      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-200"
      : tone === "red"
      ? "bg-red-500/10 border-red-500/30 text-red-200"
      : "bg-indigo-500/10 border-indigo-500/30 text-indigo-200";

  return (
    <div className="space-y-3">
      {rows.slice(0, 10).map((r, idx) => (
        <div
          key={`${r[labelKey]}-${idx}`}
          className="bg-gray-950/40 border border-gray-800 rounded-xl px-4 py-3 flex items-center justify-between"
        >
          <div className="text-gray-200 font-semibold">
            {r[labelKey]}
          </div>

          <span
            className={`text-xs px-2 py-1 rounded-lg border ${pill}`}
          >
            ${Math.round(Number(r[valueKey] || 0)).toLocaleString()}
          </span>
        </div>
      ))}

      {rows.length === 0 && (
        <div className="text-gray-500 text-sm">
          No data.
        </div>
      )}
    </div>
  );
}

export default function AccountsAnalytics() {
  const [days, setDays] = useState(30);
  const [topN, setTopN] = useState(5);

  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [anomalies, setAnomalies] = useState(null);

  const extractErrorDetail = (e) => {
    return (
      e?.response?.data?.detail ||
      e?.message ||
      "Failed to fetch accounts analytics."
    );
  };

  const fetchOverview = async () => {
    setLoading(true);
    setError("");

    try {

      const res = await api.get(
        "/analytics/accounts/overview",
        {
          params: {
            days,
            top_n: topN,
          },
        }
      );

      setData(res.data);
      const an = await api.get("/analytics/accounts/anomalies", { params: { days: Math.max(days, 90) } });
      setAnomalies(an.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    } finally {
      setLoading(false);
    }
  };

  /*
   * Fetch automatically whenever the filters change.
   */
  useEffect(() => {
    fetchOverview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, topN]);
  useAnalyticsRefresh("accounts", fetchOverview);
  const income =
    data?.income_vs_expenses?.income ?? 0;

  const expenses =
    data?.income_vs_expenses?.expenses ?? 0;

  const net =
    data?.income_vs_expenses?.net ?? 0;

  const score30 =
    data?.liquidity?.score_30d;

  const score365 =
    data?.liquidity?.score_365d;

  const scoreTone = (score) => {
    if (score >= 80) return "emerald";
    if (score >= 55) return "indigo";
    return "red";
  };

  const titleGradient =
    "bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent";

  const money = formatMoney;

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">

        {/* Header */}
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1
              className={`text-4xl font-bold mb-2 ${titleGradient}`}
            >
              Accounts Analytics
            </h1>

            <p className="text-gray-400">
              Income vs expenses, category distributions,
              liquidity score and top counterparties.
            </p>
          </div>

          <div className="flex gap-3 items-center">

            <select
              className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-2"
              value={days}
              onChange={(e) =>
                setDays(Number(e.target.value))
              }
            >
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
              <option value={365}>Last 365 days</option>
            </select>

            <select
              className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-2"
              value={topN}
              onChange={(e) =>
                setTopN(Number(e.target.value))
              }
            >
              <option value={3}>Top 3</option>
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
            </select>

            <button
              onClick={fetchOverview}
              disabled={loading}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-4 py-2 rounded-xl transition"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>

          </div>
        </div>

        <div className="mt-8"><InsightsPanel module="accounts" /></div>

        {/* Error */}
        {error && (
          <div className="mt-6 bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">
              Error
            </div>

            <div className="text-sm mt-1">
              {error}
            </div>
          </div>
        )}

        {/* Loading */}
        {loading && !data && (
          <div className="mt-8 text-gray-500">
            Loading accounts analytics...
          </div>
        )}

        {!data && !loading && (
          <div className="mt-8 text-gray-500">
            No analytics data available.
          </div>
        )}

        {data && (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-12 gap-6 mt-8">

              <div className="col-span-12 md:col-span-4">
                <MetricCard
                  title="Income"
                  value={money(income)}
                  tone="emerald"
                />
              </div>

              <div className="col-span-12 md:col-span-4">
                <MetricCard
                  title="Expenses"
                  value={money(expenses)}
                  tone="red"
                />
              </div>

              <div className="col-span-12 md:col-span-4">
                <MetricCard
                  title="Net"
                  value={money(net)}
                  tone={net >= 0 ? "indigo" : "red"}
                />
              </div>

            </div>

            {/* Income vs Expenses + Liquidity */}
            <div className="grid grid-cols-12 gap-6 mt-8">

              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title="Income vs Expenses"
                  subtitle={`Window: last ${data.window_days} days`}
                >
                  <DonutChart
                    income={income}
                    expenses={expenses}
                  />
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title="Cashflow / Liquidity Score"
                  subtitle="Higher score means healthier recent cashflow and better buffer"
                >
                  <div className="grid grid-cols-12 gap-4">

                    <div className="col-span-12 md:col-span-6">
                      <MetricCard
                        title="Liquidity Score (30d)"
                        value={score30?.score ?? "-"}
                        tone={scoreTone(
                          score30?.score ?? 0
                        )}
                        sub={
                          score30
                            ? `Buffer: ${
                                score30.buffer_days ?? "N/A"
                              } days • Avg daily debit: ${score30.avg_daily_debit}`
                            : ""
                        }
                      />
                    </div>

                    <div className="col-span-12 md:col-span-6">
                      <MetricCard
                        title="Liquidity Score (365d)"
                        value={score365?.score ?? "-"}
                        tone={scoreTone(
                          score365?.score ?? 0
                        )}
                        sub={
                          score365
                            ? `Buffer: ${
                                score365.buffer_days ?? "N/A"
                              } days • Avg daily debit: ${score365.avg_daily_debit}`
                            : ""
                        }
                      />
                    </div>

                  </div>
                </Panel>
              </div>

            </div>

            {/* Category distributions */}
            <div className="grid grid-cols-12 gap-6 mt-8">

              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title="Income by Category"
                  subtitle="Distribution of credits across categories"
                >
                  <DistributionBars
                    rows={
                      data.income_by_category || []
                    }
                    tone="emerald"
                  />
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title="Expenses by Category"
                  subtitle="Distribution of debits across categories"
                >
                  <DistributionBars
                    rows={
                      data.expense_by_category || []
                    }
                    tone="indigo"
                  />
                </Panel>
              </div>

            </div>

            {/* Rankings */}
            <div className="grid grid-cols-12 gap-6 mt-8">

              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title={`Top Income Sources (last ${data.window_days} days)`}
                  subtitle="Highest total credits by source"
                >
                  <RankingList
                    rows={
                      data.rankings?.top_income_sources || []
                    }
                    labelKey="source"
                    valueKey="amount"
                    tone="emerald"
                  />
                </Panel>
              </div>

              <div className="col-span-12 xl:col-span-6">
                <Panel
                  title={`Top Expense Targets (last ${data.window_days} days)`}
                  subtitle="Highest total debits by target"
                >
                  <RankingList
                    rows={
                      data.rankings?.top_expense_targets || []
                    }
                    labelKey="target"
                    valueKey="amount"
                    tone="red"
                  />
                </Panel>
              </div>

            </div>

            <div className="mt-8">
              <Panel
                title="Unusual transactions"
                subtitle={anomalies ? `Outliers among ${anomalies.scanned} transactions in the last ${anomalies.window_days} days, compared within each category` : "Scanning…"}
              >
                <ul className="space-y-2 text-sm">
                  {(anomalies?.anomalies || []).map((a) => (
                    <li key={a.transaction_id} className="flex justify-between gap-4 border-b border-gray-800 pb-2">
                      <span>
                        <span className={a.transaction_type === "credit" ? "text-emerald-300" : "text-red-300"}>
                          {money(a.amount)}
                        </span>{" "}
                        <span className="text-gray-300">{a.category}</span>
                        <span className="text-gray-500"> · {a.source_target} · {new Date(a.date).toLocaleDateString()}</span>
                        <span className="block text-xs text-gray-500">{a.reason}</span>
                      </span>
                      <span className="text-xs text-yellow-300 whitespace-nowrap">score {a.score}</span>
                    </li>
                  ))}
                  {anomalies && anomalies.anomalies.length === 0 && (
                    <li className="text-gray-500">No unusual transactions detected.</li>
                  )}
                </ul>
              </Panel>
            </div>
          </>
        )}

      </div>
    </div>
  );
}