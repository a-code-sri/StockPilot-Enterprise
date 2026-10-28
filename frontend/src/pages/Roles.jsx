import { useCallback, useEffect, useMemo, useState } from "react";

import Sidebar from "../components/Sidebar";
import api from "../api";
import { MOCK_MODE } from "../config";

const modules = [
  "inventory",
  "accounts",
  "delivery",
  "projects",
  "analytics",
];

const mockRoles = [
  {
    id: 1,
    name: "admin",
    permissions: [
      { name: "inventory.read" },
      { name: "inventory.write" },
      { name: "accounts.read" },
      { name: "accounts.write" },
      { name: "delivery.read" },
      { name: "delivery.write" },
      { name: "projects.read" },
      { name: "projects.write" },
      { name: "analytics.read" },
      { name: "rbac.manage" },
    ],
  },
  {
    id: 2,
    name: "inventory_manager",
    permissions: [
      { name: "inventory.read" },
      { name: "inventory.write" },
    ],
  },
];

function Toggle({ checked, onChange, label }) {
  const handleKeyDown = (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onChange();
    }
  };

  return (
    <label className="inline-flex items-center gap-2 cursor-pointer select-none">
      <span className="sr-only">{label}</span>

      <span
        className={[
          "relative inline-flex h-6 w-11 items-center rounded-full transition",
          checked ? "bg-indigo-600" : "bg-gray-700",
          "border border-gray-600",
        ].join(" ")}
        onClick={onChange}
        onKeyDown={handleKeyDown}
        role="switch"
        aria-checked={checked}
        tabIndex={0}
      >
        <span
          className={[
            "inline-block h-5 w-5 transform rounded-full bg-white transition",
            checked ? "translate-x-5" : "translate-x-1",
          ].join(" ")}
        />
      </span>

      <span
        className={
          checked
            ? "text-indigo-200 text-sm"
            : "text-gray-400 text-sm"
        }
      >
        {label}
      </span>
    </label>
  );
}

export default function Roles() {
  const [roles, setRoles] = useState([]);

  const [roleName, setRoleName] = useState("");
  const [access, setAccess] = useState({});

  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deletingRole, setDeletingRole] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // ------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------

  const extractErrorDetail = (error) =>
    error?.response?.data?.detail ||
    error?.message ||
    "Something went wrong.";

  // ------------------------------------------------------------
  // Load roles
  // ------------------------------------------------------------

  const fetchRoles = useCallback(async () => {
    setError("");

    if (MOCK_MODE) {
      setRoles(mockRoles);
      return;
    }

    setLoading(true);

    try {
      const response = await api.get("/rbac/");

      setRoles(response.data || []);
    } catch (error) {
      setError(extractErrorDetail(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  // ------------------------------------------------------------
  // Permission helpers
  // ------------------------------------------------------------

  const isChecked = (module, type) => {
    const moduleAccess = access[module] || [];

    return moduleAccess.includes(type);
  };

  const toggleAccess = (module, type) => {
    setAccess((previous) => {
      const moduleAccess = previous[module] || [];

      const updated = moduleAccess.includes(type)
        ? moduleAccess.filter((permission) => permission !== type)
        : [...moduleAccess, type];

      return {
        ...previous,
        [module]: updated,
      };
    });
  };

  // ------------------------------------------------------------
  // Create role
  // ------------------------------------------------------------

  const createRole = async () => {
    setError("");
    setSuccess("");

    const trimmedName = roleName.trim();

    if (!trimmedName) {
      setError("Role name is required.");
      return;
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(trimmedName)) {
      setError(
        "Role name may contain only letters, numbers, underscores, and hyphens."
      );
      return;
    }

    const hasPermission = Object.values(access).some(
      (permissions) => permissions.length > 0
    );

    if (!hasPermission) {
      setError("Select at least one permission.");
      return;
    }

    if (roles.some((role) => role.name === trimmedName)) {
      setError("A role with this name already exists.");
      return;
    }

    if (MOCK_MODE) {
      const newRole = {
        id: Date.now(),
        name: trimmedName,
        permissions: Object.entries(access).flatMap(
          ([module, actions]) =>
            actions.map((action) => ({
              name: `${module}.${action}`,
            }))
        ),
      };

      setRoles((previous) => [...previous, newRole]);
      setRoleName("");
      setAccess({});
      setSuccess(`Role "${trimmedName}" created successfully.`);
      return;
    }

    setCreating(true);

    try {
      const response = await api.post("/rbac/", {
        name: trimmedName,
        access,
      });

      setRoles((previous) => [
        ...previous,
        response.data,
      ]);

      setRoleName("");
      setAccess({});
      setSuccess(`Role "${trimmedName}" created successfully.`);
    } catch (error) {
      setError(extractErrorDetail(error));
    } finally {
      setCreating(false);
    }
  };

  // ------------------------------------------------------------
  // Delete role
  // ------------------------------------------------------------

  const deleteRole = async (name) => {
    if (name === "admin") {
      setError("The admin role cannot be deleted.");
      return;
    }

    setError("");
    setSuccess("");

    if (!window.confirm(`Delete role "${name}"?`)) {
      return;
    }

    if (MOCK_MODE) {
      setRoles((previous) =>
        previous.filter((role) => role.name !== name)
      );

      setSuccess(`Role "${name}" deleted successfully.`);
      return;
    }

    setDeletingRole(name);

    try {
      await api.delete(
        `/rbac/${encodeURIComponent(name)}`
      );

      setRoles((previous) =>
        previous.filter((role) => role.name !== name)
      );

      setSuccess(`Role "${name}" deleted successfully.`);
    } catch (error) {
      setError(extractErrorDetail(error));
    } finally {
      setDeletingRole("");
    }
  };

  // ------------------------------------------------------------
  // Access summary
  // ------------------------------------------------------------

  const accessSummary = useMemo(() => {
    const summary = [];

    for (const module of modules) {
      const permissions = access[module] || [];

      if (permissions.length) {
        summary.push(
          `${module}: ${permissions.join(", ")}`
        );
      }
    }

    return summary.length
      ? summary.join(" • ")
      : "No permissions selected yet.";
  }, [access]);

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
              Role Management
            </h1>

            <p className="text-gray-400">
              Create roles using a permission matrix.
            </p>
          </div>

          <button
            onClick={fetchRoles}
            disabled={loading}
            className="bg-gray-900 border border-gray-800 hover:border-indigo-500/60 px-4 py-2 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        {/* -------------------------------------------------- */}
        {/* Messages */}
        {/* -------------------------------------------------- */}

        {error && (
          <div className="mt-6 bg-red-950/40 border border-red-900 text-red-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Error</div>

            <div className="text-sm mt-1">
              {error}
            </div>
          </div>
        )}

        {success && (
          <div className="mt-6 bg-emerald-950/40 border border-emerald-900 text-emerald-200 px-4 py-3 rounded-xl">
            <div className="font-semibold">Success</div>

            <div className="text-sm mt-1">
              {success}
            </div>
          </div>
        )}

        {/* -------------------------------------------------- */}
        {/* Create Role */}
        {/* -------------------------------------------------- */}

        <div className="mt-8 bg-gray-900 border border-gray-800 p-8 rounded-2xl">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="font-semibold text-lg">
                Create Role
              </h2>

              <p className="text-xs text-gray-500 mt-1">
                {accessSummary}
              </p>
            </div>

            <button
              onClick={createRole}
              disabled={creating}
              className="bg-indigo-600 hover:bg-indigo-700 px-6 py-2.5 rounded-xl transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? "Creating..." : "Create Role"}
            </button>
          </div>

          {/* Role name */}
          <div className="mt-6 flex flex-wrap gap-4 items-center">
            <div className="w-full md:w-80">
              <label className="text-xs text-gray-400">
                Role Name
              </label>

              <input
                className="mt-2 w-full bg-gray-800 border border-gray-700 focus:border-indigo-500/70 outline-none rounded-xl px-4 py-3"
                placeholder="e.g. inventory_manager"
                value={roleName}
                onChange={(event) =>
                  setRoleName(event.target.value)
                }
              />
            </div>
          </div>

          {/* ------------------------------------------------ */}
          {/* Permissions Matrix */}
          {/* ------------------------------------------------ */}

          <div className="mt-8 bg-gray-950/40 border border-gray-800 rounded-2xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
                <tr>
                  <th className="p-4 text-left">
                    Module
                  </th>

                  <th className="p-4 text-left">
                    Read
                  </th>

                  <th className="p-4 text-left">
                    Write
                  </th>
                </tr>
              </thead>

              <tbody>
                {modules.map((module) => (
                  <tr
                    key={module}
                    className="border-t border-gray-800 hover:bg-gray-900/50 transition"
                  >
                    <td className="p-4">
                      <span className="font-semibold text-indigo-200 capitalize">
                        {module}
                      </span>
                    </td>

                    <td className="p-4">
                      <Toggle
                        label="Read"
                        checked={isChecked(
                          module,
                          "read"
                        )}
                        onChange={() =>
                          toggleAccess(
                            module,
                            "read"
                          )
                        }
                      />
                    </td>

                    <td className="p-4">
                      <Toggle
                        label="Write"
                        checked={isChecked(
                          module,
                          "write"
                        )}
                        onChange={() =>
                          toggleAccess(
                            module,
                            "write"
                          )
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-gray-500 mt-4">
            Admin is immutable and always has full access.
          </p>
        </div>

        {/* -------------------------------------------------- */}
        {/* Existing Roles */}
        {/* -------------------------------------------------- */}

        <div className="mt-8 bg-gray-900 border border-gray-800 p-8 rounded-2xl">
          <h2 className="font-semibold mb-6 text-lg">
            Existing Roles
          </h2>

          {loading ? (
            <div className="text-gray-500">
              Loading roles...
            </div>
          ) : (
            <div className="space-y-3">
              {roles.map((role) => (
                <div
                  key={role.id ?? role.name}
                  className="bg-gray-950/40 border border-gray-800 rounded-2xl px-5 py-4"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <span className="h-2.5 w-2.5 rounded-full bg-indigo-400/70 shadow-[0_0_18px_rgba(129,140,248,0.35)]" />

                      <span className="font-semibold">
                        {role.name}
                      </span>

                      {role.name === "admin" && (
                        <span className="text-xs px-2 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-200">
                          protected
                        </span>
                      )}
                    </div>

                    {role.name !== "admin" ? (
                      <button
                        onClick={() =>
                          deleteRole(role.name)
                        }
                        disabled={
                          deletingRole === role.name
                        }
                        className="text-red-300 hover:text-red-400 bg-red-500/10 border border-red-500/20 px-4 py-2 rounded-xl transition disabled:opacity-50"
                      >
                        {deletingRole === role.name
                          ? "Deleting..."
                          : "Delete"}
                      </button>
                    ) : (
                      <span className="text-xs text-gray-500">
                        Cannot delete
                      </span>
                    )}
                  </div>

                  {/* Permissions */}
                  {role.permissions?.length > 0 && (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {role.permissions.map(
                        (permission) => (
                          <span
                            key={permission.name}
                            className="text-xs px-2 py-1 rounded-lg bg-gray-800 border border-gray-700 text-gray-300"
                          >
                            {permission.name}
                          </span>
                        )
                      )}
                    </div>
                  )}
                </div>
              ))}

              {roles.length === 0 && (
                <div className="text-gray-500">
                  No roles found.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}