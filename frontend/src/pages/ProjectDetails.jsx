import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import api, { errorMessage } from "../api";

function parseCsvList(s) {
  return (s || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

export default function ProjectDetails() {
  const { id } = useParams();
  const projectId = Number(id);
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState("details");

  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);

  const [simulation, setSimulation] = useState(null);

  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const [taskForm, setTaskForm] = useState({
    name: "",
    description: "",
    duration_days: "",
    optimistic: "",
    most_likely: "",
    pessimistic: "",
    predecessorsCsv: "",
    resourcesCsv: "",
  });

  const titleGradient =
    "bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent";

  const clearMessages = () => {
    setError("");
    setInfo("");
  };

  const extractErrorDetail = (e) => errorMessage(e);

  const predecessor_task_ids = useMemo(
    () =>
      parseCsvList(taskForm.predecessorsCsv)
        .map((x) => Number(x))
        .filter((n) => Number.isFinite(n)),
    [taskForm.predecessorsCsv]
  );

  const resource_employee_ids = useMemo(
    () => parseCsvList(taskForm.resourcesCsv),
    [taskForm.resourcesCsv]
  );

  const fetchProject = async () => {
    clearMessages();

    try {
      const res = await api.get(`/projects/${projectId}`);
      setProject(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const fetchTasks = async () => {
    clearMessages();

    try {
      const res = await api.get(`/projects/${projectId}/tasks`);
      setTasks(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  useEffect(() => {
    fetchProject();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    if (!project) return;
    fetchTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project]);

  const createTask = async () => {
    clearMessages();

    if (!taskForm.name.trim()) return setError("Task name is required.");
    const duration = Number(taskForm.duration_days);
    if (!Number.isFinite(duration) || duration <= 0) return setError("duration_days must be > 0.");

    // PERT optional, but if any filled then all must be filled
    const o = taskForm.optimistic === "" ? null : Number(taskForm.optimistic);
    const m = taskForm.most_likely === "" ? null : Number(taskForm.most_likely);
    const p = taskForm.pessimistic === "" ? null : Number(taskForm.pessimistic);

    const anyPert = [o, m, p].some((x) => x != null);
    const allPert = [o, m, p].every((x) => x != null);

    if (anyPert && !allPert) return setError("PERT requires optimistic, most_likely, pessimistic together.");
    if (allPert && !(o <= m && m <= p)) return setError("PERT requires optimistic <= most_likely <= pessimistic.");

    try {
      await api.post(`/projects/${projectId}/tasks`, {
        name: taskForm.name.trim(),
        description: taskForm.description?.trim() || null,
        duration_days: duration,
        optimistic: o,
        most_likely: m,
        pessimistic: p,
        predecessor_task_ids,
        resource_employee_ids,
      });

      setInfo("Task created.");
      setTaskForm({
        name: "",
        description: "",
        duration_days: "",
        optimistic: "",
        most_likely: "",
        pessimistic: "",
        predecessorsCsv: "",
        resourcesCsv: "",
      });
      await fetchTasks();
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const deleteTask = async (taskId) => {
    clearMessages();

    try {
      await api.delete(`/projects/${projectId}/tasks/${taskId}`);
      setInfo("Task deleted.");
      await fetchTasks();
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const runSimulation = async () => {
    clearMessages();

    if (!project) return;

    try {
      const res = await api.post(`/projects/${projectId}/simulate`);
      setSimulation(res.data);
      setInfo("Simulation complete.");
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const criticalSet = useMemo(() => {
    const ids = simulation?.critical_path_task_ids || [];
    return new Set(ids);
  }, [simulation]);

  if (!project) {
    return (
      <div className="flex bg-gray-950 text-gray-200 min-h-screen">
        <Sidebar />
        <div className="flex-1 p-10">
          <div className="text-gray-400">Loading project...</div>
          {error && (
            <div className="mt-6 bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded-xl">
              <div className="font-semibold">Error</div>
              <div className="text-sm mt-1">{error}</div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <button
              onClick={() => navigate("/projects")}
              className="text-sm text-gray-400 hover:text-indigo-300 transition"
            >
              ← Back to Projects
            </button>
            <h1 className={`text-4xl font-bold mt-2 ${titleGradient}`}>{project.title}</h1>
            <p className="text-gray-400 mt-2 max-w-3xl">
              {project.description || "No description provided."}
            </p>

            <div className="flex flex-wrap gap-2 mt-4">
              {(project.resource_employee_ids || []).map((eid) => (
                <span
                  key={eid}
                  className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200"
                >
                  {eid}
                </span>
              ))}
              {(project.resource_employee_ids || []).length === 0 && (
                <span className="text-sm text-gray-500">No resources assigned</span>
              )}
            </div>

            <div className="mt-4 text-sm text-gray-400">
              <span className="mr-6">Start: <span className="text-gray-200">{project.start_date}</span></span>
              <span>Deadline: <span className="text-gray-200">{project.deadline}</span></span>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => {
                fetchProject();
                fetchTasks();
              }}
              className="bg-gray-900 border border-gray-800 hover:border-indigo-500/60 px-4 py-2 rounded-xl transition"
            >
              Refresh
            </button>
            <button
              onClick={runSimulation}
              className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-xl transition"
            >
              Run Simulation
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-6 bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Error</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
        )}

        {info && (
          <div className="mt-6 bg-emerald-950/30 border border-emerald-900 text-emerald-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Success</div>
            <div className="text-sm mt-1">{info}</div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex mt-8 mb-8 space-x-8 border-b border-gray-800">
          <button
            onClick={() => setActiveTab("details")}
            className={`pb-2 ${
              activeTab === "details"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Details
          </button>

          <button
            onClick={() => setActiveTab("tasks")}
            className={`pb-2 ${
              activeTab === "tasks"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Tasks (CPM/PERT)
          </button>

          <button
            onClick={() => setActiveTab("simulator")}
            className={`pb-2 ${
              activeTab === "simulator"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Simulator Output
          </button>
        </div>

        {activeTab === "details" && (
          <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl">
            <h2 className="text-lg font-semibold mb-2">Project Summary</h2>
            <p className="text-gray-400">
              Use the Tasks tab to model the project network. Run simulation to obtain critical path and schedule.
            </p>
          </div>
        )}

        {activeTab === "tasks" && (
          <>
            {/* Add Task */}
            <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl mb-8">
              <h2 className="text-lg font-semibold mb-4">Add Task</h2>

              <div className="grid grid-cols-12 gap-4">
                <div className="col-span-12 lg:col-span-4">
                  <label className="text-xs text-gray-400">Task Name</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="e.g. Install new line"
                    value={taskForm.name}
                    onChange={(e) => setTaskForm((p) => ({ ...p, name: e.target.value }))}
                  />
                </div>

                <div className="col-span-12 lg:col-span-2">
                  <label className="text-xs text-gray-400">Duration (days)</label>
                  <input
                    type="number"
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="5"
                    value={taskForm.duration_days}
                    onChange={(e) =>
                      setTaskForm((p) => ({ ...p, duration_days: e.target.value }))
                    }
                  />
                </div>

                <div className="col-span-12 lg:col-span-3">
                  <label className="text-xs text-gray-400">Predecessors (task IDs CSV)</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="1, 2"
                    value={taskForm.predecessorsCsv}
                    onChange={(e) =>
                      setTaskForm((p) => ({ ...p, predecessorsCsv: e.target.value }))
                    }
                  />
                </div>

                <div className="col-span-12 lg:col-span-3">
                  <label className="text-xs text-gray-400">Resources (employee_ids CSV)</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="E100, E101"
                    value={taskForm.resourcesCsv}
                    onChange={(e) =>
                      setTaskForm((p) => ({ ...p, resourcesCsv: e.target.value }))
                    }
                  />
                </div>

                <div className="col-span-12">
                  <label className="text-xs text-gray-400">Description</label>
                  <textarea
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3 min-h-[80px]"
                    placeholder="Optional"
                    value={taskForm.description}
                    onChange={(e) =>
                      setTaskForm((p) => ({ ...p, description: e.target.value }))
                    }
                  />
                </div>

                {/* PERT section */}
                <div className="col-span-12">
                  <div className="bg-gray-800/40 border border-gray-700 rounded-2xl p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-gray-200">PERT (Optional)</div>
                        <div className="text-xs text-gray-400 mt-1">
                          Fill all three to use expected duration = (o + 4m + p) / 6.
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-12 gap-4 mt-4">
                      <div className="col-span-12 md:col-span-4">
                        <label className="text-xs text-gray-400">Optimistic</label>
                        <input
                          type="number"
                          className="mt-2 w-full bg-gray-900 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                          placeholder="4"
                          value={taskForm.optimistic}
                          onChange={(e) =>
                            setTaskForm((p) => ({ ...p, optimistic: e.target.value }))
                          }
                        />
                      </div>

                      <div className="col-span-12 md:col-span-4">
                        <label className="text-xs text-gray-400">Most Likely</label>
                        <input
                          type="number"
                          className="mt-2 w-full bg-gray-900 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                          placeholder="5"
                          value={taskForm.most_likely}
                          onChange={(e) =>
                            setTaskForm((p) => ({ ...p, most_likely: e.target.value }))
                          }
                        />
                      </div>

                      <div className="col-span-12 md:col-span-4">
                        <label className="text-xs text-gray-400">Pessimistic</label>
                        <input
                          type="number"
                          className="mt-2 w-full bg-gray-900 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                          placeholder="7"
                          value={taskForm.pessimistic}
                          onChange={(e) =>
                            setTaskForm((p) => ({ ...p, pessimistic: e.target.value }))
                          }
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-5 flex gap-3">
                <button
                  onClick={createTask}
                  className="bg-indigo-600 hover:bg-indigo-700 px-6 py-2.5 rounded-xl transition"
                >
                  Add Task
                </button>
                <button
                  onClick={() =>
                    setTaskForm({
                      name: "",
                      description: "",
                      duration_days: "",
                      optimistic: "",
                      most_likely: "",
                      pessimistic: "",
                      predecessorsCsv: "",
                      resourcesCsv: "",
                    })
                  }
                  className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-6 py-2.5 rounded-xl transition"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Tasks Table */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
                  <tr>
                    <th className="p-4">ID</th>
                    <th className="p-4">Task</th>
                    <th className="p-4">Duration</th>
                    <th className="p-4">Preds</th>
                    <th className="p-4">Resources</th>
                    <th className="p-4">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.map((t) => (
                    <tr
                      key={t.id}
                      className="border-t border-gray-800 hover:bg-gray-800/40 transition"
                    >
                      <td className="p-4 font-mono text-indigo-300">{t.id}</td>
                      <td className="p-4">
                        <div className="font-semibold">{t.name}</div>
                        <div className="text-xs text-gray-400 mt-1">
                          {t.description || "-"}
                        </div>
                      </td>
                      <td className="p-4">
                        {t.duration_days}d
                        {t.optimistic != null && (
                          <div className="text-xs text-gray-400 mt-1">
                            PERT: ({t.optimistic}, {t.most_likely}, {t.pessimistic})
                          </div>
                        )}
                      </td>
                      <td className="p-4 text-gray-300">
                        {(t.predecessor_task_ids || []).join(", ") || "-"}
                      </td>
                      <td className="p-4">
                        <div className="flex flex-wrap gap-2">
                          {(t.resource_employee_ids || []).map((eid) => (
                            <span
                              key={`${t.id}-${eid}`}
                              className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200"
                            >
                              {eid}
                            </span>
                          ))}
                          {(t.resource_employee_ids || []).length === 0 && (
                            <span className="text-gray-500 text-sm">-</span>
                          )}
                        </div>
                      </td>
                      <td className="p-4">
                        <button
                          onClick={() => deleteTask(t.id)}
                          className="bg-red-600 hover:bg-red-700 px-3 py-2 rounded-xl transition"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}

                  {tasks.length === 0 && (
                    <tr>
                      <td className="p-6 text-gray-500" colSpan={6}>
                        No tasks created yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {activeTab === "simulator" && (
          <>
            <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl mb-8">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold">CPM/PERT Simulation</h2>
                  <p className="text-sm text-gray-400 mt-1">
                    Computes critical path, schedule (ES/EF/LS/LF/Float), and resource overlaps.
                  </p>
                </div>
                <button
                  onClick={runSimulation}
                  className="bg-indigo-600 hover:bg-indigo-700 px-5 py-2.5 rounded-xl transition"
                >
                  Run Simulation
                </button>
              </div>
            </div>

            {!simulation ? (
              <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl text-gray-400">
                Run simulation to see output.
              </div>
            ) : (
              <>
                {/* Summary cards */}
                <div className="grid grid-cols-12 gap-4 mb-8">
                  <Card
                    title="Project Duration (days)"
                    value={simulation.project_duration_days?.toFixed?.(2) ?? simulation.project_duration_days}
                    accent="indigo"
                  />
                  <Card
                    title="Deadline Slack (days)"
                    value={simulation.deadline_days_remaining?.toFixed?.(2) ?? simulation.deadline_days_remaining}
                    accent={simulation.deadline_days_remaining >= 0 ? "green" : "red"}
                  />
                  <Card
                    title="Critical Path Task IDs"
                    value={(simulation.critical_path_task_ids || []).join(" → ") || "-"}
                    accent="purple"
                    wide
                  />
                </div>

                {/* Schedule table */}
                <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden mb-8">
                  <div className="p-4 border-b border-gray-800">
                    <h3 className="font-semibold">Schedule (CPM)</h3>
                    <p className="text-xs text-gray-400 mt-1">
                      Critical tasks highlighted. Float ~ 0 indicates critical.
                    </p>
                  </div>

                  <table className="w-full">
                    <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
                      <tr>
                        <th className="p-4">Task</th>
                        <th className="p-4">Dur</th>
                        <th className="p-4">ES</th>
                        <th className="p-4">EF</th>
                        <th className="p-4">LS</th>
                        <th className="p-4">LF</th>
                        <th className="p-4">Float</th>
                        <th className="p-4">Planned</th>
                        <th className="p-4">Resources</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(simulation.tasks || []).map((t) => {
                        const isCritical = criticalSet.has(t.id);
                        return (
                          <tr
                            key={t.id}
                            className={`border-t border-gray-800 hover:bg-gray-800/40 transition ${
                              isCritical ? "bg-indigo-500/10" : ""
                            }`}
                          >
                            <td className="p-4">
                              <div className="font-semibold">
                                <span className="font-mono text-indigo-300 mr-2">{t.id}</span>
                                {t.name}
                              </div>
                              <div className="text-xs text-gray-400 mt-1">
                                Preds: {(t.predecessor_task_ids || []).join(", ") || "-"}
                              </div>
                            </td>
                            <td className="p-4">{Number(t.expected_duration_days).toFixed(2)}</td>
                            <td className="p-4">{Number(t.ES).toFixed(2)}</td>
                            <td className="p-4">{Number(t.EF).toFixed(2)}</td>
                            <td className="p-4">{Number(t.LS).toFixed(2)}</td>
                            <td className="p-4">{Number(t.LF).toFixed(2)}</td>
                            <td className="p-4">{Number(t.float).toFixed(2)}</td>
                            <td className="p-4 text-sm text-gray-300">
                              <div>{t.planned_start}</div>
                              <div className="text-gray-500">→ {t.planned_end}</div>
                            </td>
                            <td className="p-4">
                              <div className="flex flex-wrap gap-2">
                                {(t.resource_employee_ids || []).map((eid) => (
                                  <span
                                    key={`${t.id}-${eid}`}
                                    className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200"
                                  >
                                    {eid}
                                  </span>
                                ))}
                                {(t.resource_employee_ids || []).length === 0 && (
                                  <span className="text-gray-500 text-sm">-</span>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}

                      {(simulation.tasks || []).length === 0 && (
                        <tr>
                          <td className="p-6 text-gray-500" colSpan={9}>
                            No schedule output.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Resource conflicts */}
                <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl">
                  <h3 className="font-semibold">Resource Conflicts</h3>
                  <p className="text-xs text-gray-400 mt-1">
                    Overlaps indicate tasks scheduled at the same time using the same employee.
                  </p>

                  {Object.keys(simulation.resource_conflicts || {}).length === 0 ? (
                    <div className="text-gray-400 mt-4">No resource conflicts detected.</div>
                  ) : (
                    <div className="mt-4 space-y-4">
                      {Object.entries(simulation.resource_conflicts).map(([emp, conflicts]) => (
                        <div
                          key={emp}
                          className="bg-gray-800/40 border border-gray-700 rounded-2xl p-4"
                        >
                          <div className="font-semibold text-indigo-200">Employee: {emp}</div>
                          <div className="mt-3 space-y-2">
                            {conflicts.map((c, idx) => (
                              <div
                                key={idx}
                                className="flex flex-wrap items-center justify-between gap-2 text-sm"
                              >
                                <span className="text-gray-300">
                                  Task {c.task_a} ↔ Task {c.task_b}
                                </span>
                                <span className="text-red-300">
                                  Overlap: {Number(c.overlap_days).toFixed(2)} days
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function Card({ title, value, accent = "indigo", wide = false }) {
  const accentMap = {
    indigo: "text-indigo-300",
    purple: "text-purple-300",
    green: "text-emerald-300",
    red: "text-red-300",
  };

  return (
    <div
      className={`bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-lg ${
        wide ? "col-span-12 lg:col-span-6" : "col-span-12 md:col-span-6 lg:col-span-3"
      }`}
    >
      <div className="text-xs text-gray-400 uppercase tracking-wide">{title}</div>
      <div className={`mt-3 text-2xl font-bold ${accentMap[accent] || "text-indigo-300"}`}>
        {value}
      </div>
    </div>
  );
}