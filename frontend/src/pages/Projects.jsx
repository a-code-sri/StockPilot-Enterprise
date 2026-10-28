import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import api from "../api";
import { MOCK_MODE } from "../config";

const MOCK_PROJECTS_KEY = "mock_projects";
const MOCK_TASKS_KEY = "mock_project_tasks";

function ensureMockSeed() {
  const existing = localStorage.getItem(MOCK_PROJECTS_KEY);
  if (!existing) {
    const seed = [
      {
        id: 1,
        title: "Factory Expansion Phase-1",
        description: "Expand production line capacity and upgrade packaging.",
        start_date: "2026-08-01",
        deadline: "2026-09-15",
        created_at: new Date().toISOString(),
        resource_employee_ids: ["E100", "E101"],
      },
      {
        id: 2,
        title: "Inventory System Upgrade",
        description: "Improve tracking + reconcile legacy stock.",
        start_date: "2026-08-05",
        deadline: "2026-08-30",
        created_at: new Date().toISOString(),
        resource_employee_ids: ["E101"],
      },
    ];
    localStorage.setItem(MOCK_PROJECTS_KEY, JSON.stringify(seed));
  }

  const existingTasks = localStorage.getItem(MOCK_TASKS_KEY);
  if (!existingTasks) {
    const seedTasks = {
      "1": [
        {
          id: 1,
          project_id: 1,
          name: "Design Layout",
          description: "Layout + equipment placement plan",
          duration_days: 5,
          optimistic: 4,
          most_likely: 5,
          pessimistic: 7,
          predecessor_task_ids: [],
          resource_employee_ids: ["E100"],
          created_at: new Date().toISOString(),
        },
        {
          id: 2,
          project_id: 1,
          name: "Procure Equipment",
          description: "Procurement & vendor follow-ups",
          duration_days: 10,
          optimistic: null,
          most_likely: null,
          pessimistic: null,
          predecessor_task_ids: [1],
          resource_employee_ids: ["E101"],
          created_at: new Date().toISOString(),
        },
      ],
      "2": [],
    };
    localStorage.setItem(MOCK_TASKS_KEY, JSON.stringify(seedTasks));
  }
}

function loadMockProjects() {
  ensureMockSeed();
  return JSON.parse(localStorage.getItem(MOCK_PROJECTS_KEY) || "[]");
}

function saveMockProjects(projects) {
  localStorage.setItem(MOCK_PROJECTS_KEY, JSON.stringify(projects));
}

export default function Projects() {
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const [form, setForm] = useState({
    title: "",
    description: "",
    start_date: "",
    deadline: "",
    resourcesCsv: "",
  });

  const titleGradient =
    "bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent";

  const clearMessages = () => {
    setError("");
    setInfo("");
  };

  const extractErrorDetail = (e) => {
    const detail =
      e?.response?.data?.detail ||
      e?.message ||
      "Something went wrong. Please try again.";
    return typeof detail === "string" ? detail : JSON.stringify(detail);
  };

  const resource_employee_ids = useMemo(() => {
    return form.resourcesCsv
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }, [form.resourcesCsv]);

  const fetchProjects = async () => {
    clearMessages();
    if (MOCK_MODE) {
      setProjects(loadMockProjects());
      return;
    }

    try {
      const res = await api.get("/projects/");
      setProjects(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  useEffect(() => {
    fetchProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const createProject = async () => {
    clearMessages();

    if (!form.title.trim()) return setError("Project title is required.");
    if (!form.start_date) return setError("Start date is required.");
    if (!form.deadline) return setError("Deadline is required.");

    if (MOCK_MODE) {
      const existing = loadMockProjects();
      const dup = existing.some(
        (p) => p.title.toLowerCase() === form.title.trim().toLowerCase()
      );
      if (dup) return setError("Could not create project: title already exists (mock).");

      const nextId = existing.length ? Math.max(...existing.map((p) => p.id)) + 1 : 1;

      const newProject = {
        id: nextId,
        title: form.title.trim(),
        description: form.description?.trim() || null,
        start_date: form.start_date,
        deadline: form.deadline,
        created_at: new Date().toISOString(),
        resource_employee_ids,
      };

      const updated = [newProject, ...existing];
      saveMockProjects(updated);
      setProjects(updated);

      setInfo("Project created (mock).");
      setForm({
        title: "",
        description: "",
        start_date: "",
        deadline: "",
        resourcesCsv: "",
      });
      return;
    }

    try {
      await api.post("/projects/", {
        title: form.title.trim(),
        description: form.description?.trim() || null,
        start_date: form.start_date,
        deadline: form.deadline,
        resource_employee_ids,
      });

      setInfo("Project created.");
      setForm({
        title: "",
        description: "",
        start_date: "",
        deadline: "",
        resourcesCsv: "",
      });
      await fetchProjects();
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const deleteProject = async (projectId) => {
    clearMessages();

    if (MOCK_MODE) {
      const existing = loadMockProjects();
      const updated = existing.filter((p) => p.id !== projectId);
      saveMockProjects(updated);
      setProjects(updated);
      setInfo("Project deleted (mock).");
      return;
    }

    try {
      await api.delete(`/projects/${projectId}`);
      setInfo("Project deleted.");
      await fetchProjects();
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className={`text-4xl font-bold mb-2 ${titleGradient}`}>Projects</h1>
            <p className="text-gray-400">
              Manage projects and open a project to build CPM/PERT task networks.
            </p>
          </div>

          <button
            onClick={fetchProjects}
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

        {info && (
          <div className="mt-6 bg-emerald-950/30 border border-emerald-900 text-emerald-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Success</div>
            <div className="text-sm mt-1">{info}</div>
          </div>
        )}

        {/* Create Project */}
        <div className="mt-8 bg-gray-900 border border-gray-800 p-6 rounded-2xl">
          <h2 className="text-lg font-semibold mb-4">Create Project</h2>

          <div className="grid grid-cols-12 gap-4">
            <div className="col-span-12 lg:col-span-4">
              <label className="text-xs text-gray-400">Title</label>
              <input
                className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                placeholder="Project title"
                value={form.title}
                onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
              />
            </div>

            <div className="col-span-12 lg:col-span-4">
              <label className="text-xs text-gray-400">Resources (employee_ids CSV)</label>
              <input
                className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                placeholder="E100, E101"
                value={form.resourcesCsv}
                onChange={(e) =>
                  setForm((p) => ({ ...p, resourcesCsv: e.target.value }))
                }
              />
            </div>

            <div className="col-span-6 lg:col-span-2">
              <label className="text-xs text-gray-400">Start Date</label>
              <input
                type="date"
                className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                value={form.start_date}
                onChange={(e) =>
                  setForm((p) => ({ ...p, start_date: e.target.value }))
                }
              />
            </div>

            <div className="col-span-6 lg:col-span-2">
              <label className="text-xs text-gray-400">Deadline</label>
              <input
                type="date"
                className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                value={form.deadline}
                onChange={(e) =>
                  setForm((p) => ({ ...p, deadline: e.target.value }))
                }
              />
            </div>

            <div className="col-span-12">
              <label className="text-xs text-gray-400">Description</label>
              <textarea
                className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3 min-h-[90px]"
                placeholder="Project description (optional)"
                value={form.description}
                onChange={(e) =>
                  setForm((p) => ({ ...p, description: e.target.value }))
                }
              />
            </div>
          </div>

          <div className="mt-5 flex gap-3">
            <button
              onClick={createProject}
              className="bg-indigo-600 hover:bg-indigo-700 px-6 py-2.5 rounded-xl transition"
            >
              Create
            </button>
            <button
              onClick={() =>
                setForm({
                  title: "",
                  description: "",
                  start_date: "",
                  deadline: "",
                  resourcesCsv: "",
                })
              }
              className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-6 py-2.5 rounded-xl transition"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Projects Table */}
        <div className="mt-8 bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
              <tr>
                <th className="p-4">Title</th>
                <th className="p-4">Start</th>
                <th className="p-4">Deadline</th>
                <th className="p-4">Resources</th>
                <th className="p-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr
                  key={p.id}
                  className="border-t border-gray-800 hover:bg-gray-800/40 transition cursor-pointer"
                  onClick={() => navigate(`/projects/${p.id}`)}
                >
                  <td className="p-4 font-semibold text-indigo-200">{p.title}</td>
                  <td className="p-4">{p.start_date}</td>
                  <td className="p-4">{p.deadline}</td>
                  <td className="p-4">
                    <span className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200">
                      {(p.resource_employee_ids || []).length} people
                    </span>
                  </td>
                  <td className="p-4" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => navigate(`/projects/${p.id}`)}
                      className="bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded-xl transition mr-2"
                    >
                      Open
                    </button>
                    <button
                      onClick={() => deleteProject(p.id)}
                      className="bg-red-600 hover:bg-red-700 px-3 py-2 rounded-xl transition"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}

              {projects.length === 0 && (
                <tr>
                  <td className="p-6 text-gray-500" colSpan={5}>
                    No projects found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-gray-500 mt-4">
          Tip: click any row to open project details and run CPM/PERT simulation.
        </p>
      </div>
    </div>
  );
}