import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api";
import { useAnalyticsRefresh } from "../realtime/RealtimeProvider";
import { ErrorBanner, InsightsPanel, Page, Panel, buttonClass } from "../components/ui";
import { dateTime, number } from "../lib/format";

function Stat({ label, value, tone = "text-indigo-300" }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
      <div className="text-xs text-gray-400 uppercase">{label}</div>
      <div className={`mt-3 text-3xl font-bold ${tone}`}>{value}</div>
    </div>
  );
}

function SlackBar({ slack, window }) {
  if (slack === null || slack === undefined) return <span className="text-red-300 text-xs">dependency loop</span>;
  const used = window > 0 ? Math.min(100, Math.max(0, ((window - slack) / window) * 100)) : 100;
  const color = slack < 0 ? "bg-red-500" : slack < window * 0.1 ? "bg-yellow-400" : "bg-emerald-500";
  return (
    <div className="w-40">
      <div className="h-2 rounded bg-gray-800 overflow-hidden">
        <div className={`h-2 ${color}`} style={{ width: `${used}%` }} />
      </div>
      <div className={`text-xs mt-1 ${slack < 0 ? "text-red-300" : "text-gray-400"}`}>
        {slack < 0 ? `${number(-slack, 1)} days late` : `${number(slack, 1)} days spare`}
      </div>
    </div>
  );
}

export default function ProjectsAnalytics() {
  const [overview, setOverview] = useState(null);
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [o, p] = await Promise.all([api.get("/analytics/projects/overview"), api.get("/analytics/projects/projects")]);
      setOverview(o.data);
      setProjects(p.data);
    } catch (err) {
      setError(errorMessage(err, "Could not load project analytics"));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useAnalyticsRefresh("projects", load);

  return (
    <Page title="Projects Analytics" subtitle={overview?.last_updated ? `Updated ${dateTime(overview.last_updated)}` : "Schedule risk across the portfolio"}
      actions={<button className={buttonClass.secondary} onClick={load}>Refresh</button>}>
      <ErrorBanner message={error} onClose={() => setError("")} />
      <InsightsPanel module="projects" />

      {overview && (
        <div className="grid gap-4 sm:grid-cols-3 mb-8">
          <Stat label="Projects" value={overview.projects_total} />
          <Stat label="At risk of missing deadline" value={overview.projects_at_risk} tone={overview.projects_at_risk ? "text-red-300" : "text-emerald-300"} />
          <Stat label="Past deadline" value={overview.projects_overdue ?? 0} tone="text-yellow-300" />
        </div>
      )}

      <Panel title="Schedule health" subtitle="Expected duration (critical path, PERT-weighted) versus the time available before the deadline.">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-400 uppercase text-left">
              <tr>
                <th className="pb-2">Project</th><th className="pb-2">Deadline</th><th className="pb-2 text-right">Tasks</th>
                <th className="pb-2 text-right">Expected days</th><th className="pb-2">Slack</th><th className="pb-2">Critical path</th>
              </tr>
            </thead>
            <tbody>
              {projects.length === 0 && <tr><td colSpan={6} className="py-4 text-gray-500">No projects yet.</td></tr>}
              {projects.map((p) => (
                <tr key={p.project_id} className="border-t border-gray-800 align-top">
                  <td className="py-3"><Link to={`/projects/${p.project_id}`} className="text-indigo-300 hover:underline">{p.title}</Link></td>
                  <td className="py-3 text-gray-400">{p.deadline}</td>
                  <td className="py-3 text-right">{p.task_count}</td>
                  <td className="py-3 text-right">
                    {number(p.critical_path.duration_days, 1)}
                    {p.critical_path.std_dev_days > 0 && (
                      <span className="text-xs text-gray-500"> ± {number(p.critical_path.std_dev_days, 1)}</span>
                    )}
                  </td>
                  <td className="py-3"><SlackBar slack={p.schedule.slack_days} window={p.schedule.window_days} /></td>
                  <td className="py-3 text-gray-400 text-xs">{p.critical_path.task_names.join(" → ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </Page>
  );
}
