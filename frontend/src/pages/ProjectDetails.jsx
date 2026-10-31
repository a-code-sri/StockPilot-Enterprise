import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";
import { number } from "../lib/format";

const csv = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

/** Pick employees from a list when we can read the organization; otherwise type IDs. */
function PeoplePicker({ employees, value, onChange }) {
  if (!employees) {
    return (
      <input className={`${inputClass} w-full`} placeholder="Employee IDs, comma separated"
        value={value.join(", ")} onChange={(e) => onChange(csv(e.target.value))} />
    );
  }
  if (employees.length === 0) return <p className="text-sm text-gray-500">No employees yet (add them under Organization).</p>;
  return (
    <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto">
      {employees.map((e) => {
        const on = value.includes(e.employee_id);
        return (
          <label key={e.employee_id}
            className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs cursor-pointer ${
              on ? "border-indigo-500/60 bg-indigo-500/15 text-indigo-200" : "border-gray-700 text-gray-400"
            }`}>
            <input type="checkbox" className="sr-only" checked={on}
              onChange={() => onChange(on ? value.filter((x) => x !== e.employee_id) : [...value, e.employee_id])} />
            {e.name} <span className="text-gray-500">{e.employee_id}</span>
          </label>
        );
      })}
    </div>
  );
}

function ProjectForm({ project, employees, onSaved, onCancel, onError }) {
  const [form, setForm] = useState({
    title: project.title, description: project.description || "", start_date: project.start_date,
    deadline: project.deadline, resource_employee_ids: project.resource_employee_ids,
  });
  const set = (f) => (e) => setForm({ ...form, [f]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    try {
      const res = await api.put(`/projects/${project.id}`, { ...form, description: form.description.trim() || null });
      onSaved(res.data);
    } catch (err) {
      onError(errorMessage(err, "Could not save project"));
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <input className={`${inputClass} w-80`} required minLength={2} maxLength={200} value={form.title} onChange={set("title")} aria-label="Title" />
        <label className="flex items-center gap-2 text-sm text-gray-400">Start
          <input className={inputClass} type="date" required value={form.start_date} onChange={set("start_date")} /></label>
        <label className="flex items-center gap-2 text-sm text-gray-400">Deadline
          <input className={inputClass} type="date" required min={form.start_date} value={form.deadline} onChange={set("deadline")} /></label>
      </div>
      <textarea className={`${inputClass} w-full min-h-[70px]`} maxLength={5000} placeholder="Description"
        value={form.description} onChange={set("description")} />
      <div>
        <div className="text-xs uppercase text-gray-400 mb-2">Team</div>
        <PeoplePicker employees={employees} value={form.resource_employee_ids}
          onChange={(ids) => setForm({ ...form, resource_employee_ids: ids })} />
      </div>
      <div className="flex gap-2">
        <button className={buttonClass.primary}>Save project</button>
        <button type="button" className={buttonClass.secondary} onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

const EMPTY_TASK = { name: "", description: "", duration_days: "", usePert: false, optimistic: "", most_likely: "", pessimistic: "",
  predecessor_task_ids: [], resource_employee_ids: [] };

function TaskForm({ projectId, tasks, employees, editing, onSaved, onCancel, onError }) {
  const [form, setForm] = useState(() =>
    editing
      ? { ...EMPTY_TASK, ...editing, description: editing.description || "", duration_days: String(editing.duration_days),
          usePert: editing.optimistic != null, optimistic: editing.optimistic ?? "", most_likely: editing.most_likely ?? "",
          pessimistic: editing.pessimistic ?? "" }
      : EMPTY_TASK
  );
  const set = (f) => (e) => setForm({ ...form, [f]: e.target.value });
  const others = tasks.filter((t) => t.id !== editing?.id);

  const submit = async (e) => {
    e.preventDefault();
    const num = (v) => (v === "" ? null : Number(v));
    const body = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      duration_days: Number(form.duration_days),
      optimistic: form.usePert ? num(form.optimistic) : null,
      most_likely: form.usePert ? num(form.most_likely) : null,
      pessimistic: form.usePert ? num(form.pessimistic) : null,
      predecessor_task_ids: form.predecessor_task_ids,
      resource_employee_ids: form.resource_employee_ids,
    };
    try {
      if (editing) await api.put(`/projects/${projectId}/tasks/${editing.id}`, body);
      else await api.post(`/projects/${projectId}/tasks`, body);
      onSaved();
    } catch (err) {
      onError(errorMessage(err, "Could not save task"));
    }
  };

  const toggleDep = (id) =>
    setForm({ ...form, predecessor_task_ids: form.predecessor_task_ids.includes(id)
      ? form.predecessor_task_ids.filter((x) => x !== id) : [...form.predecessor_task_ids, id] });

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <input className={`${inputClass} w-72`} required maxLength={200} placeholder="Task name" value={form.name} onChange={set("name")} />
        <input className={`${inputClass} w-36`} required type="number" min="0.1" step="0.1" placeholder="Duration (days)"
          value={form.duration_days} onChange={set("duration_days")} />
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={form.usePert} onChange={(e) => setForm({ ...form, usePert: e.target.checked })} />
          Uncertain? Use three-point (PERT) estimate
        </label>
      </div>
      {form.usePert && (
        <div className="flex flex-wrap gap-3 items-center text-sm text-gray-400">
          <input className={`${inputClass} w-28`} required type="number" min="0.1" step="0.1" placeholder="Best case" value={form.optimistic} onChange={set("optimistic")} />
          <input className={`${inputClass} w-28`} required type="number" min="0.1" step="0.1" placeholder="Most likely" value={form.most_likely} onChange={set("most_likely")} />
          <input className={`${inputClass} w-28`} required type="number" min="0.1" step="0.1" placeholder="Worst case" value={form.pessimistic} onChange={set("pessimistic")} />
          <span>days — scheduling uses (best + 4×likely + worst) / 6</span>
        </div>
      )}
      <textarea className={`${inputClass} w-full`} maxLength={5000} placeholder="Description (optional)" value={form.description} onChange={set("description")} />
      <div>
        <div className="text-xs uppercase text-gray-400 mb-2">Can only start after</div>
        {others.length === 0 ? <p className="text-sm text-gray-500">No other tasks yet.</p> : (
          <div className="flex flex-wrap gap-2">
            {others.map((t) => (
              <label key={t.id} className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs cursor-pointer ${
                form.predecessor_task_ids.includes(t.id) ? "border-indigo-500/60 bg-indigo-500/15 text-indigo-200" : "border-gray-700 text-gray-400"}`}>
                <input type="checkbox" className="sr-only" checked={form.predecessor_task_ids.includes(t.id)} onChange={() => toggleDep(t.id)} />
                {t.name}
              </label>
            ))}
          </div>
        )}
      </div>
      <div>
        <div className="text-xs uppercase text-gray-400 mb-2">People</div>
        <PeoplePicker employees={employees} value={form.resource_employee_ids}
          onChange={(ids) => setForm({ ...form, resource_employee_ids: ids })} />
      </div>
      <div className="flex gap-2">
        <button className={buttonClass.primary}>{editing ? "Save task" : "Add task"}</button>
        {onCancel && <button type="button" className={buttonClass.secondary} onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}

function Gantt({ simulation, windowDays }) {
  const span = Math.max(simulation.project_duration_days, windowDays, 1);
  const critical = new Set(simulation.critical_path_task_ids);
  const pct = (d) => `${(d / span) * 100}%`;
  return (
    <div className="space-y-2">
      {simulation.tasks.map((t) => (
        <div key={t.id} className="grid grid-cols-[180px_1fr] items-center gap-3 text-sm">
          <div className="truncate" title={t.name}>{t.name}</div>
          <div className="relative h-6 rounded bg-gray-800/60">
            <div className="absolute top-0 bottom-0 border-r-2 border-dashed border-red-400/70" style={{ left: pct(windowDays) }}
              title="Deadline" />
            <div
              className={`absolute top-1 bottom-1 rounded ${critical.has(t.id) ? "bg-red-500/80" : "bg-indigo-500/70"}`}
              style={{ left: pct(t.ES), width: `max(${pct(t.EF - t.ES)}, 4px)` }}
              title={`${t.planned_start} → ${t.planned_end} · ${number(t.expected_duration_days, 1)} days · slack ${number(t.float, 1)}`}
            />
          </div>
        </div>
      ))}
      <div className="grid grid-cols-[180px_1fr] gap-3 text-xs text-gray-500">
        <div />
        <div className="flex justify-between"><span>day 0</span><span>day {number(span, 0)}</span></div>
      </div>
      <p className="text-xs text-gray-500">
        <span className="inline-block w-3 h-3 rounded bg-red-500/80 align-middle" /> critical path (any delay moves the end date) ·{" "}
        <span className="inline-block w-3 h-3 rounded bg-indigo-500/70 align-middle" /> has slack · dashed line = deadline
      </p>
    </div>
  );
}

export default function ProjectDetails() {
  const { id } = useParams();
  const projectId = Number(id);
  const { can } = useAuth();
  const canWrite = can("projects.write");

  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [simulation, setSimulation] = useState(null);
  const [employees, setEmployees] = useState(null);
  const [editingProject, setEditingProject] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [taskFormKey, setTaskFormKey] = useState(0);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, t] = await Promise.all([api.get(`/projects/${projectId}`), api.get(`/projects/${projectId}/tasks`)]);
      setProject(p.data);
      setTasks(t.data);
      try {
        setSimulation((await api.post(`/projects/${projectId}/simulate`)).data);
      } catch (err) {
        setSimulation(null);
        setError(errorMessage(err, "Could not schedule this project"));
      }
    } catch (err) {
      setError(errorMessage(err, "Could not load project"));
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!can("organization.read")) return;
    api.get("/organization/employees", { params: { limit: 1000 } }).then((r) => setEmployees(r.data)).catch(() => {});
  }, [can]);

  const taskName = useMemo(() => Object.fromEntries(tasks.map((t) => [t.id, t.name])), [tasks]);
  const personName = useMemo(
    () => Object.fromEntries((employees || []).map((e) => [e.employee_id, e.name])), [employees]);

  const deleteTask = async (t) => {
    if (!window.confirm(`Delete task "${t.name}"? Tasks that depend on it will no longer wait for it.`)) return;
    try {
      await api.delete(`/projects/${projectId}/tasks/${t.id}`);
      if (editingTask?.id === t.id) setEditingTask(null);
      load();
    } catch (err) {
      setError(errorMessage(err, "Could not delete task"));
    }
  };

  if (!project) {
    return (
      <Page title="Project">
        <ErrorBanner message={error} />
        {!error && <p className="text-gray-400">Loading…</p>}
      </Page>
    );
  }

  const windowDays = Math.round((new Date(project.deadline) - new Date(project.start_date)) / 86400000);
  const spare = simulation?.deadline_days_remaining;

  return (
    <Page
      title={project.title}
      subtitle={`${project.start_date} → ${project.deadline} · ${windowDays} days available`}
      actions={
        <>
          <Link to="/projects" className={buttonClass.secondary}>← All projects</Link>
          {canWrite && !editingProject && (
            <button className={buttonClass.primary} onClick={() => setEditingProject(true)}>Edit project</button>
          )}
        </>
      }
    >
      <ErrorBanner message={error} onClose={() => setError("")} />

      {editingProject ? (
        <Panel title="Edit project" className="mb-8">
          <ProjectForm project={project} employees={employees} onError={setError} onCancel={() => setEditingProject(false)}
            onSaved={(p) => { setProject(p); setEditingProject(false); load(); }} />
        </Panel>
      ) : (
        <Panel className="mb-8" title="About">
          <p className="text-sm text-gray-300 whitespace-pre-wrap">{project.description || "No description."}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {project.resource_employee_ids.length === 0 && <span className="text-sm text-gray-500">No team assigned.</span>}
            {project.resource_employee_ids.map((eid) => (
              <span key={eid} className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200">
                {personName[eid] ? `${personName[eid]} (${eid})` : eid}
              </span>
            ))}
          </div>
        </Panel>
      )}

      {simulation && simulation.tasks.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-3 mb-6">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
              <div className="text-xs text-gray-400 uppercase">Expected duration</div>
              <div className="mt-2 text-2xl font-bold text-indigo-300">
                {number(simulation.project_duration_days, 1)} days
                {simulation.project_std_dev_days > 0 && (
                  <span className="text-sm text-gray-400 font-normal"> ± {number(simulation.project_std_dev_days, 1)}</span>
                )}
              </div>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
              <div className="text-xs text-gray-400 uppercase">{spare >= 0 ? "Days to spare" : "Days late"}</div>
              <div className={`mt-2 text-2xl font-bold ${spare >= 0 ? "text-emerald-300" : "text-red-300"}`}>{number(Math.abs(spare), 1)}</div>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
              <div className="text-xs text-gray-400 uppercase">Critical path</div>
              <div className="mt-2 text-sm text-gray-200">
                {simulation.critical_path_task_ids.map((tid) => taskName[tid]).join(" → ")}
              </div>
            </div>
          </div>

          <Panel title="Timeline" subtitle="Earliest schedule from the task dependencies (CPM/PERT). Hover a bar for dates." className="mb-6">
            <Gantt simulation={simulation} windowDays={windowDays} />
          </Panel>

          {Object.keys(simulation.resource_conflicts).length > 0 && (
            <Panel title="People double-booked" className="mb-6"
              subtitle="These people are on overlapping tasks in the schedule above.">
              <ul className="text-sm space-y-1">
                {Object.entries(simulation.resource_conflicts).map(([emp, list]) => (
                  <li key={emp}>
                    <span className="text-yellow-300">{personName[emp] || emp}</span>:{" "}
                    {list.map((c) => `${taskName[c.task_a]} & ${taskName[c.task_b]} (${number(c.overlap_days, 1)} days)`).join("; ")}
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </>
      )}

      {canWrite && (
        <Panel className="mb-6" title={editingTask ? `Edit "${editingTask.name}"` : "Add task"}>
          <TaskForm
            key={editingTask ? `edit-${editingTask.id}` : `new-${taskFormKey}`}
            projectId={projectId}
            tasks={tasks}
            employees={employees}
            editing={editingTask}
            onError={setError}
            onCancel={editingTask ? () => setEditingTask(null) : null}
            onSaved={() => { setEditingTask(null); setTaskFormKey((k) => k + 1); setError(""); load(); }}
          />
        </Panel>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400 text-xs uppercase text-left">
            <tr><th className="p-3">Task</th><th className="p-3">Duration</th><th className="p-3">After</th><th className="p-3">People</th>{canWrite && <th className="p-3" />}</tr>
          </thead>
          <tbody>
            {tasks.length === 0 && <tr><td colSpan={5} className="p-6 text-center text-gray-500">No tasks yet.</td></tr>}
            {tasks.map((t) => (
              <tr key={t.id} className={`border-t border-gray-800 ${editingTask?.id === t.id ? "bg-indigo-500/10" : ""}`}>
                <td className="p-3">
                  {t.name}
                  {simulation?.critical_path_task_ids.includes(t.id) && <span className="ml-2 text-xs text-red-300">critical</span>}
                  {t.description && <div className="text-xs text-gray-500">{t.description}</div>}
                </td>
                <td className="p-3 whitespace-nowrap">
                  {t.optimistic != null ? `${t.optimistic} / ${t.most_likely} / ${t.pessimistic} days` : `${t.duration_days} days`}
                </td>
                <td className="p-3 text-gray-400">{t.predecessor_task_ids.map((p) => taskName[p]).join(", ") || "—"}</td>
                <td className="p-3 text-gray-400">{t.resource_employee_ids.map((e) => personName[e] || e).join(", ") || "—"}</td>
                {canWrite && (
                  <td className="p-3 whitespace-nowrap text-right space-x-2">
                    <button className={buttonClass.small} onClick={() => { setEditingTask(t); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Edit</button>
                    <button className={buttonClass.danger} onClick={() => deleteTask(t)}>Delete</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  );
}
