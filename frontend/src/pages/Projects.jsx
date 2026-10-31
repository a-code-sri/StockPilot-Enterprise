import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";

const EMPTY = { title: "", description: "", start_date: "", deadline: "", resourcesCsv: "" };

const csv = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

export default function Projects() {
  const navigate = useNavigate();
  const { can } = useAuth();
  const canWrite = can("projects.write");

  const [projects, setProjects] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");

  const fetchProjects = useCallback(async () => {
    try {
      setProjects((await api.get("/projects/")).data);
    } catch (err) {
      setError(errorMessage(err, "Could not load projects"));
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const createProject = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/projects/", {
        title: form.title.trim(),
        description: form.description.trim() || null,
        start_date: form.start_date,
        deadline: form.deadline,
        resource_employee_ids: csv(form.resourcesCsv),
      });
      setForm(EMPTY);
      navigate(`/projects/${res.data.id}`);
    } catch (err) {
      setError(errorMessage(err, "Could not create project"));
    }
  };

  const deleteProject = async (p) => {
    if (!window.confirm(`Delete project "${p.title}" and all its tasks?`)) return;
    try {
      await api.delete(`/projects/${p.id}`);
      fetchProjects();
    } catch (err) {
      setError(errorMessage(err, "Could not delete project"));
    }
  };

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <Page title="Projects" subtitle="Open a project to build its task network and run CPM/PERT scheduling."
      actions={<button className={buttonClass.secondary} onClick={fetchProjects}>Refresh</button>}>
      <ErrorBanner message={error} onClose={() => setError("")} />

      {canWrite && (
        <Panel title="Create project" className="mb-8">
          <form onSubmit={createProject} className="space-y-3">
            <div className="flex flex-wrap gap-3">
              <input className={`${inputClass} w-72`} required minLength={2} maxLength={200} placeholder="Title"
                value={form.title} onChange={set("title")} />
              <label className="flex items-center gap-2 text-sm text-gray-400">
                Start <input className={inputClass} type="date" required value={form.start_date} onChange={set("start_date")} />
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-400">
                Deadline <input className={inputClass} type="date" required min={form.start_date || undefined}
                  value={form.deadline} onChange={set("deadline")} />
              </label>
              <input className={`${inputClass} w-72`} placeholder="Team (employee IDs, comma separated)"
                value={form.resourcesCsv} onChange={set("resourcesCsv")} />
            </div>
            <textarea className={`${inputClass} w-full min-h-[70px]`} maxLength={5000} placeholder="Description (optional)"
              value={form.description} onChange={set("description")} />
            <button className={buttonClass.primary}>Create</button>
          </form>
        </Panel>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400 text-xs uppercase text-left">
            <tr><th className="p-3">Title</th><th className="p-3">Start</th><th className="p-3">Deadline</th><th className="p-3">Team</th><th className="p-3" /></tr>
          </thead>
          <tbody>
            {projects.length === 0 && (
              <tr><td colSpan={5} className="p-6 text-center text-gray-500">No projects yet.</td></tr>
            )}
            {projects.map((p) => (
              <tr key={p.id} className="border-t border-gray-800 hover:bg-gray-800/40 cursor-pointer" onClick={() => navigate(`/projects/${p.id}`)}>
                <td className="p-3 font-medium text-indigo-200">{p.title}</td>
                <td className="p-3">{p.start_date}</td>
                <td className="p-3">{p.deadline}</td>
                <td className="p-3 text-gray-400">{p.resource_employee_ids.join(", ") || "—"}</td>
                <td className="p-3 text-right whitespace-nowrap space-x-2" onClick={(e) => e.stopPropagation()}>
                  <button className={buttonClass.small} onClick={() => navigate(`/projects/${p.id}`)}>Open</button>
                  {canWrite && <button className={buttonClass.danger} onClick={() => deleteProject(p)}>Delete</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  );
}
