import { useCallback, useEffect, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import OrgChart from "../components/OrgChart";
import Pager from "../components/Pager";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";
import { date, money } from "../lib/format";
import "../styles/orgChart.css";

const PAGE_SIZE = 100;
const EMPTY = { employee_id: "", name: "", salary: "", job_role: "", manager_employee_id: "", departments: [] };

function DepartmentPicker({ all, value, onChange }) {
  if (all.length === 0) return <p className="text-sm text-gray-500">No departments yet. Create one in the Departments tab.</p>;
  return (
    <div className="flex flex-wrap gap-2">
      {all.map((d) => {
        const on = value.includes(d.name);
        return (
          <label key={d.id}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-sm cursor-pointer ${
              on ? "bg-indigo-500/10 border-indigo-500/40" : "bg-gray-800 border-gray-700"
            }`}>
            <input type="checkbox" checked={on}
              onChange={() => onChange(on ? value.filter((x) => x !== d.name) : [...value, d.name])} />
            {d.name}
          </label>
        );
      })}
    </div>
  );
}

function EmployeeForm({ departments, initial, editing, onSubmit, onCancel }) {
  const [form, setForm] = useState(initial);
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const submit = (e) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <input className={inputClass} required maxLength={50} placeholder="Employee ID" value={form.employee_id}
          disabled={editing} onChange={set("employee_id")} />
        <input className={inputClass} required maxLength={200} placeholder="Full name" value={form.name} onChange={set("name")} />
        <input className={`${inputClass} w-32`} required type="number" min="0" step="0.01" placeholder="Salary" value={form.salary} onChange={set("salary")} />
        <input className={inputClass} required maxLength={200} placeholder="Job role" value={form.job_role} onChange={set("job_role")} />
        <input className={inputClass} maxLength={50} placeholder="Manager employee ID (optional)" value={form.manager_employee_id ?? ""}
          onChange={set("manager_employee_id")} />
      </div>
      <DepartmentPicker all={departments} value={form.departments} onChange={(departments) => setForm({ ...form, departments })} />
      <div className="flex gap-3">
        <button className={buttonClass.primary}>{editing ? "Save changes" : "Add employee"}</button>
        {onCancel && <button type="button" className={buttonClass.secondary} onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}

export default function Organization() {
  const { can } = useAuth();
  const canWrite = can("organization.write");

  const [tab, setTab] = useState("employees");
  const [employees, setEmployees] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [departments, setDepartments] = useState([]);
  const [chartEmployees, setChartEmployees] = useState([]);
  const [filters, setFilters] = useState({ q: "", department: "", manager_employee_id: "" });
  const [editing, setEditing] = useState(null);
  const [formKey, setFormKey] = useState(0);
  const [newDept, setNewDept] = useState("");
  const [error, setError] = useState("");

  const fetchDepartments = useCallback(async () => {
    try {
      setDepartments((await api.get("/organization/departments")).data);
    } catch (err) {
      setError(errorMessage(err, "Could not load departments"));
    }
  }, []);

  const fetchEmployees = useCallback(async () => {
    try {
      const params = { limit: PAGE_SIZE, offset };
      for (const [k, v] of Object.entries(filters)) if (v.trim()) params[k] = v.trim();
      const res = await api.get("/organization/employees", { params });
      setEmployees(res.data);
      setTotal(Number(res.headers["x-total-count"] ?? res.data.length));
    } catch (err) {
      setError(errorMessage(err, "Could not load employees"));
    }
  }, [filters, offset]);

  useEffect(() => {
    fetchDepartments();
  }, [fetchDepartments]);

  useEffect(() => {
    const t = setTimeout(fetchEmployees, 250);
    return () => clearTimeout(t);
  }, [fetchEmployees]);

  useEffect(() => {
    if (tab !== "hierarchy") return;
    api.get("/organization/employees", { params: { limit: 1000 } })
      .then((r) => setChartEmployees(r.data))
      .catch((err) => setError(errorMessage(err, "Could not load hierarchy")));
  }, [tab]);

  const reloadAll = () => {
    fetchEmployees();
    fetchDepartments();
  };

  const saveEmployee = async (form) => {
    setError("");
    const body = {
      name: form.name.trim(),
      salary: Number(form.salary),
      job_role: form.job_role.trim(),
      manager_employee_id: (form.manager_employee_id || "").trim() || null,
      departments: form.departments,
    };
    try {
      if (editing) {
        await api.put(`/organization/employees/${encodeURIComponent(editing.employee_id)}`, body);
        setEditing(null);
      } else {
        await api.post("/organization/employees", { ...body, employee_id: form.employee_id.trim() });
        setFormKey((k) => k + 1); // reset the create form
      }
      reloadAll();
    } catch (err) {
      setError(errorMessage(err, "Could not save employee"));
    }
  };

  const deleteEmployee = async (emp) => {
    if (!window.confirm(`Delete ${emp.name} (${emp.employee_id})? Their reports will have no manager.`)) return;
    try {
      await api.delete(`/organization/employees/${encodeURIComponent(emp.employee_id)}`);
      reloadAll();
    } catch (err) {
      setError(errorMessage(err, "Could not delete employee"));
    }
  };

  const createDepartment = async (e) => {
    e.preventDefault();
    try {
      await api.post("/organization/departments", { name: newDept.trim() });
      setNewDept("");
      fetchDepartments();
    } catch (err) {
      setError(errorMessage(err, "Could not create department"));
    }
  };

  const deleteDepartment = async (d) => {
    if (!window.confirm(`Delete department "${d.name}"?`)) return;
    try {
      await api.delete(`/organization/departments/${encodeURIComponent(d.name)}`);
      fetchDepartments();
    } catch (err) {
      setError(errorMessage(err, "Could not delete department"));
    }
  };

  const setFilter = (field) => (e) => {
    setFilters({ ...filters, [field]: e.target.value });
    setOffset(0);
  };

  return (
    <Page title="Organization" subtitle="Employees, departments and reporting lines">
      <ErrorBanner message={error} onClose={() => setError("")} />

      <div role="tablist" className="flex mb-6 gap-6 border-b border-gray-800">
        {[["employees", "Employees"], ["departments", "Departments"], ["hierarchy", "Hierarchy"]].map(([id, text]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={`pb-2 ${tab === id ? "border-b-2 border-indigo-500 text-indigo-300" : "text-gray-400"}`}>
            {text}
          </button>
        ))}
      </div>

      {tab === "employees" && (
        <>
          {canWrite && (
            <Panel title={editing ? `Edit ${editing.name}` : "Add employee"} className="mb-6">
              <EmployeeForm
                key={editing ? `edit-${editing.employee_id}` : `new-${formKey}`}
                departments={departments}
                editing={Boolean(editing)}
                initial={editing ? { ...editing, salary: String(editing.salary) } : EMPTY}
                onSubmit={saveEmployee}
                onCancel={editing ? () => setEditing(null) : null}
              />
            </Panel>
          )}

          <div className="flex flex-wrap gap-3 mb-4">
            <input className={`${inputClass} w-72`} placeholder="Search ID, name or role" value={filters.q} onChange={setFilter("q")} aria-label="Search" />
            <select className={inputClass} value={filters.department} onChange={setFilter("department")} aria-label="Department">
              <option value="">All departments</option>
              {departments.map((d) => <option key={d.id} value={d.name}>{d.name}</option>)}
            </select>
            <input className={inputClass} placeholder="Reports to (employee ID)" value={filters.manager_employee_id}
              onChange={setFilter("manager_employee_id")} aria-label="Manager" />
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 text-gray-400 text-xs uppercase text-left">
                <tr>
                  <th className="p-3">ID</th><th className="p-3">Name</th><th className="p-3">Role</th>
                  <th className="p-3 text-right">Salary</th><th className="p-3">Manager</th><th className="p-3">Departments</th>
                  {canWrite && <th className="p-3" />}
                </tr>
              </thead>
              <tbody>
                {employees.length === 0 && (
                  <tr><td colSpan={7} className="p-6 text-center text-gray-500">No employees found.</td></tr>
                )}
                {employees.map((e) => (
                  <tr key={e.employee_id} className="border-t border-gray-800 hover:bg-gray-800/40">
                    <td className="p-3 font-mono text-indigo-300">{e.employee_id}</td>
                    <td className="p-3">{e.name}</td>
                    <td className="p-3 text-gray-300">{e.job_role}</td>
                    <td className="p-3 text-right">{money(e.salary)}</td>
                    <td className="p-3">{e.manager_employee_id || "—"}</td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-1">
                        {e.departments.map((d) => (
                          <span key={d} className="text-xs px-2 py-0.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200">{d}</span>
                        ))}
                      </div>
                    </td>
                    {canWrite && (
                      <td className="p-3 whitespace-nowrap text-right space-x-2">
                        <button className={buttonClass.small} onClick={() => { setEditing(e); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Edit</button>
                        <button className={buttonClass.danger} onClick={() => deleteEmployee(e)}>Delete</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager offset={offset} limit={PAGE_SIZE} total={total} onChange={setOffset} />
        </>
      )}

      {tab === "departments" && (
        <>
          {canWrite && (
            <Panel title="Create department" className="mb-6">
              <form onSubmit={createDepartment} className="flex gap-3">
                <input className={`${inputClass} w-80`} required minLength={2} maxLength={100} placeholder="e.g. Sales"
                  value={newDept} onChange={(e) => setNewDept(e.target.value)} />
                <button className={buttonClass.primary}>Create</button>
              </form>
            </Panel>
          )}
          <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 text-gray-400 text-xs uppercase text-left">
                <tr><th className="p-3">Department</th><th className="p-3 text-right">Headcount</th><th className="p-3">Created</th>{canWrite && <th className="p-3" />}</tr>
              </thead>
              <tbody>
                {departments.length === 0 && (
                  <tr><td colSpan={4} className="p-6 text-center text-gray-500">No departments.</td></tr>
                )}
                {departments.map((d) => (
                  <tr key={d.id} className="border-t border-gray-800">
                    <td className="p-3">{d.name}</td>
                    <td className="p-3 text-right">{d.headcount}</td>
                    <td className="p-3 text-gray-400">{date(d.created_at)}</td>
                    {canWrite && (
                      <td className="p-3 text-right">
                        <button className={buttonClass.danger} disabled={d.headcount > 0}
                          title={d.headcount > 0 ? "Reassign its employees first" : undefined}
                          onClick={() => deleteDepartment(d)}>Delete</button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "hierarchy" && <OrgChart employees={chartEmployees} />}
    </Page>
  );
}
