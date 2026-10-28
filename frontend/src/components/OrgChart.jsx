import React, { useMemo } from "react";

/**
 * employees: Array of objects like:
 * {
 *   employee_id: "E101",
 *   name: "Sara Khan",
 *   job_role: "Inventory Lead",
 *   salary: 60000,
 *   manager_employee_id: "E100" | null,
 *   departments: ["Operations"]
 * }
 */
export default function OrgChart({ employees }) {
  const { roots, childrenByManager } = useMemo(() => {
    const byId = new Map();
    for (const e of employees || []) byId.set(e.employee_id, e);

    const childrenMap = new Map(); // manager_employee_id -> [employee]
    for (const e of employees || []) {
      const mgr = e.manager_employee_id || null;
      if (!childrenMap.has(mgr)) childrenMap.set(mgr, []);
      childrenMap.get(mgr).push(e);
    }

    // Sort children for stable layout
    for (const [k, arr] of childrenMap.entries()) {
      arr.sort((a, b) => (a.employee_id || "").localeCompare(b.employee_id || ""));
      childrenMap.set(k, arr);
    }

    // Roots: manager is null OR manager not found in dataset
    const rootsList = (employees || []).filter((e) => {
      if (!e.manager_employee_id) return true;
      return !byId.has(e.manager_employee_id);
    });

    rootsList.sort((a, b) => (a.employee_id || "").localeCompare(b.employee_id || ""));

    return { roots: rootsList, childrenByManager: childrenMap };
  }, [employees]);

  const renderNode = (emp) => {
    const kids = childrenByManager.get(emp.employee_id) || [];

    return (
      <li key={emp.employee_id}>
        <div className="node">
          <div className="title">{emp.name}</div>
          <div className="subtitle">
            {emp.job_role} • <span className="font-mono">{emp.employee_id}</span>
          </div>

          <div className="meta">
            <span>Salary: ${emp.salary}</span>
            <span>Mgr: {emp.manager_employee_id || "-"}</span>
          </div>

          <div>
            {(emp.departments || []).map((d) => (
              <span key={`${emp.employee_id}-${d}`} className="chip">
                {d}
              </span>
            ))}
          </div>
        </div>

        {kids.length > 0 && (
          <ul className="clearfix">
            {kids.map((k) => renderNode(k))}
          </ul>
        )}
      </li>
    );
  };

  if (!employees || employees.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 p-6 rounded-2xl text-gray-400">
        No employees found to build hierarchy.
      </div>
    );
  }

  return (
    <div className="orgchart">
      {roots.map((root) => (
        <div key={root.employee_id} className="tree">
          <ul className="clearfix">{renderNode(root)}</ul>
        </div>
      ))}
    </div>
  );
}