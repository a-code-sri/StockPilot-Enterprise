import { useEffect, useMemo, useState } from "react";
import Sidebar from "../components/Sidebar";
import api from "../api";
import OrgChart from "../components/OrgChart";
import "../styles/orgChart.css";
import { MOCK_MODE } from "../config";

const initialEmployeeForm = {
  employee_id: "",
  name: "",
  salary: "",
  job_role: "",
  manager_employee_id: "",
  departments: [],
};

export default function Organization() {
  const [activeTab, setActiveTab] = useState("employees");

  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);

  const [employeeForm, setEmployeeForm] = useState(initialEmployeeForm);
  const [newDeptName, setNewDeptName] = useState("");

  const [searchQ, setSearchQ] = useState("");
  const [filterDept, setFilterDept] = useState("");
  const [filterManager, setFilterManager] = useState("");

  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [allEmployeesForChart, setAllEmployeesForChart] = useState([]);
  // --------- Mock state (only used when MOCK_MODE = true)
  const fetchAllEmployeesForHierarchy = async () => {
    clearMessages();

    if (MOCK_MODE) {
      // Use full mock list (not filtered)
      setAllEmployeesForChart(mockEmployees);
      return;
    }

    try {
      const res = await api.get("/organization/employees"); // no params => all
      setAllEmployeesForChart(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };
  useEffect(() => {
    if (activeTab === "hierarchy") {
      fetchAllEmployeesForHierarchy();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);
  const [mockEmployees, setMockEmployees] = useState([
    {
      id: 1,
      employee_id: "E100",
      name: "Aarav Mehta",
      salary: 90000,
      job_role: "Plant Manager",
      manager_employee_id: null,
      departments: ["Operations"],
      created_at: "2026-08-01T00:00:00Z",
    },
    {
      id: 2,
      employee_id: "E101",
      name: "Sara Khan",
      salary: 60000,
      job_role: "Inventory Lead",
      manager_employee_id: "E100",
      departments: ["Operations", "Warehouse"],
      created_at: "2026-08-02T00:00:00Z",
    },
  ]);

  const [mockDepartments, setMockDepartments] = useState([
    { id: 1, name: "Operations", created_at: "2026-08-01T00:00:00Z" },
    { id: 2, name: "Warehouse", created_at: "2026-08-01T00:00:00Z" },
    { id: 3, name: "Finance", created_at: "2026-08-01T00:00:00Z" },
  ]);

  const deptNames = useMemo(() => departments.map((d) => d.name), [departments]);

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

  // ---------- Load initial data
  useEffect(() => {
    (async () => {
      await fetchDepartments();
      await fetchEmployees();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------- API calls
  const fetchDepartments = async () => {
    clearMessages();

    if (MOCK_MODE) {
      setDepartments(mockDepartments);
      return;
    }

    try {
      const res = await api.get("/organization/departments");
      setDepartments(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const fetchEmployees = async () => {
    clearMessages();

    if (MOCK_MODE) {
      // simple mock filtering consistent with backend query params
      let rows = [...mockEmployees];

      if (searchQ) {
        const q = searchQ.toLowerCase();
        rows = rows.filter(
          (x) =>
            x.employee_id.toLowerCase().includes(q) ||
            x.name.toLowerCase().includes(q) ||
            x.job_role.toLowerCase().includes(q)
        );
      }

      if (filterManager) {
        rows = rows.filter((x) => x.manager_employee_id === filterManager);
      }

      if (filterDept) {
        rows = rows.filter((x) => (x.departments || []).includes(filterDept));
      }

      setEmployees(rows);
      return;
    }

    try {
      const params = {};
      if (searchQ) params.q = searchQ;
      if (filterDept) params.department = filterDept;
      if (filterManager) params.manager_employee_id = filterManager;

      const res = await api.get("/organization/employees", { params });
      setEmployees(res.data);
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const createDepartment = async () => {
    clearMessages();

    const name = newDeptName.trim();
    if (!name) {
      setError("Department name cannot be empty.");
      return;
    }

    if (MOCK_MODE) {
      const exists = mockDepartments.some(
        (d) => d.name.toLowerCase() === name.toLowerCase()
      );
      if (exists) {
        setError("Department already exists.");
        return;
      }

      const created = {
        id: mockDepartments.length + 1,
        name,
        created_at: new Date().toISOString(),
      };
      const updated = [created, ...mockDepartments];
      setMockDepartments(updated);
      setDepartments(updated);
      setNewDeptName("");
      setInfo("Department created (mock).");
      return;
    }

    try {
      await api.post("/organization/departments", { name });
      setNewDeptName("");
      setInfo("Department created.");
      await fetchDepartments();
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const createEmployee = async () => {
    clearMessages();

    // Basic frontend checks (backend still enforces integrity constraints)
    if (!employeeForm.employee_id.trim()) return setError("Employee ID is required.");
    if (!employeeForm.name.trim()) return setError("Name is required.");
    if (!employeeForm.job_role.trim()) return setError("Job role is required.");
    if (employeeForm.salary === "") return setError("Salary is required.");

    const salary = Number(employeeForm.salary);
    if (Number.isNaN(salary) || salary < 0) return setError("Salary must be a non-negative number.");

    if (
      employeeForm.manager_employee_id &&
      employeeForm.manager_employee_id.trim() === employeeForm.employee_id.trim()
    ) {
      return setError("Employee cannot be their own manager.");
    }

    if (MOCK_MODE) {
      // simulate backend integrity checks
      const empId = employeeForm.employee_id.trim();
      const mgr = employeeForm.manager_employee_id.trim() || null;

      const exists = mockEmployees.some((e) => e.employee_id === empId);
      if (exists) return setError("Integrity error: employee_id must be unique and salary must be non-negative.");

      if (mgr) {
        const mgrExists = mockEmployees.some((e) => e.employee_id === mgr);
        if (!mgrExists) return setError(`Manager with employee_id '${mgr}' does not exist.`);
      }

      for (const dept of employeeForm.departments) {
        const deptExists = mockDepartments.some((d) => d.name === dept);
        if (!deptExists) return setError(`Department '${dept}' does not exist. Create it first.`);
      }

      const created = {
        id: mockEmployees.length + 1,
        employee_id: empId,
        name: employeeForm.name.trim(),
        salary,
        job_role: employeeForm.job_role.trim(),
        manager_employee_id: mgr,
        departments: employeeForm.departments,
        created_at: new Date().toISOString(),
      };

      const updated = [created, ...mockEmployees];
      setMockEmployees(updated);
      setEmployees(updated);
      setEmployeeForm(initialEmployeeForm);
      setInfo("Employee created (mock).");
      return;
    }

    try {
      await api.post("/organization/employees", {
        employee_id: employeeForm.employee_id.trim(),
        name: employeeForm.name.trim(),
        salary,
        job_role: employeeForm.job_role.trim(),
        manager_employee_id: employeeForm.manager_employee_id.trim() || null,
        departments: employeeForm.departments,
      });

      setEmployeeForm(initialEmployeeForm);
      setInfo("Employee created.");
      await fetchEmployees();
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const deleteEmployee = async (employee_id) => {
    clearMessages();

    if (!employee_id) return;

    if (MOCK_MODE) {
      const updated = mockEmployees.filter((e) => e.employee_id !== employee_id);
      setMockEmployees(updated);
      setEmployees(updated);
      setInfo("Employee deleted (mock).");
      return;
    }

    try {
      await api.delete(`/organization/employees/${employee_id}`);
      setInfo("Employee deleted.");
      await fetchEmployees();
    } catch (e) {
      setError(extractErrorDetail(e));
    }
  };

  const toggleDeptInForm = (deptName) => {
    setEmployeeForm((prev) => {
      const exists = prev.departments.includes(deptName);
      return {
        ...prev,
        departments: exists
          ? prev.departments.filter((d) => d !== deptName)
          : [...prev.departments, deptName],
      };
    });
  };

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />

      <div className="flex-1 p-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
              Organization Structure
            </h1>
            <p className="text-gray-400">
              Employees, reporting hierarchy, and departments (integrity enforced).
            </p>
          </div>

          <button
            onClick={fetchEmployees}
            className="bg-gray-900 border border-gray-800 hover:border-indigo-500/60 px-4 py-2 rounded-xl transition"
          >
            Refresh
          </button>
        </div>

        {/* Alerts */}
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
            onClick={() => setActiveTab("employees")}
            className={`pb-2 ${
              activeTab === "employees"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Employees
          </button>

          <button
            onClick={() => setActiveTab("departments")}
            className={`pb-2 ${
              activeTab === "departments"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Departments
          </button>
          <button
            onClick={() => setActiveTab("hierarchy")}
            className={`pb-2 ${
              activeTab === "hierarchy"
                ? "border-b-2 border-indigo-500 text-indigo-400"
                : "text-gray-400"
            }`}
          >
            Hierarchy
          </button>
        </div>

        {/* Employees Tab */}
        {activeTab === "employees" && (
          <>
            {/* Search + Filters */}
            <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl mb-8">
              <div className="grid grid-cols-12 gap-4">
                <div className="col-span-12 lg:col-span-6">
                  <label className="text-xs text-gray-400">Search</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="Search by employee_id / name / job role"
                    value={searchQ}
                    onChange={(e) => setSearchQ(e.target.value)}
                  />
                </div>

                <div className="col-span-12 lg:col-span-3">
                  <label className="text-xs text-gray-400">Department</label>
                  <select
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    value={filterDept}
                    onChange={(e) => setFilterDept(e.target.value)}
                  >
                    <option value="">All</option>
                    {deptNames.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-span-12 lg:col-span-3">
                  <label className="text-xs text-gray-400">Manager Employee ID</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="e.g. E100"
                    value={filterManager}
                    onChange={(e) => setFilterManager(e.target.value)}
                  />
                </div>
              </div>

              <div className="mt-4 flex gap-3">
                <button
                  onClick={fetchEmployees}
                  className="bg-indigo-600 hover:bg-indigo-700 px-5 py-2.5 rounded-xl transition"
                >
                  Search
                </button>

                <button
                  onClick={() => {
                    setSearchQ("");
                    setFilterDept("");
                    setFilterManager("");
                    setTimeout(fetchEmployees, 0);
                  }}
                  className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-5 py-2.5 rounded-xl transition"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Add Employee */}
            <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl mb-8">
              <h2 className="text-lg font-semibold mb-4">Add Employee</h2>

              <div className="grid grid-cols-12 gap-4">
                <div className="col-span-12 md:col-span-3">
                  <label className="text-xs text-gray-400">Employee ID</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="E102"
                    value={employeeForm.employee_id}
                    onChange={(e) =>
                      setEmployeeForm((p) => ({ ...p, employee_id: e.target.value }))
                    }
                  />
                </div>

                <div className="col-span-12 md:col-span-4">
                  <label className="text-xs text-gray-400">Name</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="Full name"
                    value={employeeForm.name}
                    onChange={(e) =>
                      setEmployeeForm((p) => ({ ...p, name: e.target.value }))
                    }
                  />
                </div>

                <div className="col-span-12 md:col-span-2">
                  <label className="text-xs text-gray-400">Salary</label>
                  <input
                    type="number"
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="60000"
                    value={employeeForm.salary}
                    onChange={(e) =>
                      setEmployeeForm((p) => ({ ...p, salary: e.target.value }))
                    }
                  />
                </div>

                <div className="col-span-12 md:col-span-3">
                  <label className="text-xs text-gray-400">Job Role</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="Warehouse Supervisor"
                    value={employeeForm.job_role}
                    onChange={(e) =>
                      setEmployeeForm((p) => ({ ...p, job_role: e.target.value }))
                    }
                  />
                </div>

                <div className="col-span-12 md:col-span-4">
                  <label className="text-xs text-gray-400">Manager Employee ID (optional)</label>
                  <input
                    className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                    placeholder="E100"
                    value={employeeForm.manager_employee_id}
                    onChange={(e) =>
                      setEmployeeForm((p) => ({
                        ...p,
                        manager_employee_id: e.target.value,
                      }))
                    }
                  />
                  <p className="text-xs text-gray-500 mt-2">
                    Must exist. Cannot be same as employee_id.
                  </p>
                </div>

                <div className="col-span-12 md:col-span-8">
                  <label className="text-xs text-gray-400">Departments</label>
                  <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2">
                    {deptNames.length === 0 ? (
                      <div className="text-gray-500 text-sm col-span-12">
                        No departments found. Create departments first.
                      </div>
                    ) : (
                      deptNames.map((d) => {
                        const checked = employeeForm.departments.includes(d);
                        return (
                          <label
                            key={d}
                            className={`flex items-center gap-2 px-3 py-2 rounded-xl border transition cursor-pointer ${
                              checked
                                ? "bg-indigo-500/10 border-indigo-500/40"
                                : "bg-gray-800 border-gray-700 hover:border-gray-600"
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleDeptInForm(d)}
                            />
                            <span className="text-sm">{d}</span>
                          </label>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-5 flex gap-3">
                <button
                  onClick={createEmployee}
                  className="bg-indigo-600 hover:bg-indigo-700 px-6 py-2.5 rounded-xl transition"
                >
                  Add Employee
                </button>
                <button
                  onClick={() => setEmployeeForm(initialEmployeeForm)}
                  className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-6 py-2.5 rounded-xl transition"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Employees Table */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
                  <tr>
                    <th className="p-4">Employee ID</th>
                    <th className="p-4">Name</th>
                    <th className="p-4">Job Role</th>
                    <th className="p-4">Salary</th>
                    <th className="p-4">Manager</th>
                    <th className="p-4">Departments</th>
                    <th className="p-4">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((e) => (
                    <tr
                      key={e.employee_id}
                      className="border-t border-gray-800 hover:bg-gray-800/40 transition"
                    >
                      <td className="p-4 font-mono text-indigo-300">{e.employee_id}</td>
                      <td className="p-4">{e.name}</td>
                      <td className="p-4 text-gray-300">{e.job_role}</td>
                      <td className="p-4">${e.salary}</td>
                      <td className="p-4">{e.manager_employee_id || "-"}</td>
                      <td className="p-4">
                        <div className="flex flex-wrap gap-2">
                          {(e.departments || []).map((d) => (
                            <span
                              key={`${e.employee_id}-${d}`}
                              className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200"
                            >
                              {d}
                            </span>
                          ))}
                          {(e.departments || []).length === 0 && (
                            <span className="text-gray-500 text-sm">-</span>
                          )}
                        </div>
                      </td>
                      <td className="p-4">
                        <button
                          onClick={() => deleteEmployee(e.employee_id)}
                          className="bg-red-600 hover:bg-red-700 px-3 py-2 rounded-xl transition"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}

                  {employees.length === 0 && (
                    <tr>
                      <td className="p-6 text-gray-500" colSpan={7}>
                        No employees found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* Departments Tab */}
        {activeTab === "departments" && (
          <>
            <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl mb-8">
              <h2 className="text-lg font-semibold mb-4">Create Department</h2>

              <div className="flex flex-wrap gap-3 items-center">
                <input
                  className="bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3 w-80"
                  placeholder="e.g. Sales"
                  value={newDeptName}
                  onChange={(e) => setNewDeptName(e.target.value)}
                />
                <button
                  onClick={createDepartment}
                  className="bg-indigo-600 hover:bg-indigo-700 px-6 py-3 rounded-xl transition"
                >
                  Create
                </button>
                <button
                  onClick={fetchDepartments}
                  className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-6 py-3 rounded-xl transition"
                >
                  Refresh
                </button>
              </div>

              <p className="text-xs text-gray-500 mt-3">
                Backend enforces uniqueness. If department exists, you’ll see an error.
              </p>
            </div>

            <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
                  <tr>
                    <th className="p-4">Department Name</th>
                    <th className="p-4">Created At</th>
                  </tr>
                </thead>
                <tbody>
                  {departments.map((d) => (
                    <tr
                      key={d.id}
                      className="border-t border-gray-800 hover:bg-gray-800/40 transition"
                    >
                      <td className="p-4">{d.name}</td>
                      <td className="p-4 text-gray-400">
                        {String(d.created_at).slice(0, 19).replace("T", " ")}
                      </td>
                    </tr>
                  ))}

                  {departments.length === 0 && (
                    <tr>
                      <td className="p-6 text-gray-500" colSpan={2}>
                        No departments found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
        {activeTab === "hierarchy" && (
          <>
            <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl mb-8">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold">Organization Hierarchy</h2>
                  <p className="text-sm text-gray-400 mt-1">
                    Top executive(s) appear at the top (employees with no manager or missing manager).
                  </p>
                </div>

                <button
                  onClick={fetchAllEmployeesForHierarchy}
                  className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-5 py-2.5 rounded-xl transition"
                >
                  Refresh Hierarchy
                </button>
              </div>
            </div>

            <OrgChart employees={allEmployeesForChart} />
          </>
        )}
      </div>
    </div>
  );
}