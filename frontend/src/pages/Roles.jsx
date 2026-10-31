import { useCallback, useEffect, useMemo, useState } from "react";
import api, { errorMessage } from "../api";
import { useAuth } from "../context/AuthContext";
import { ErrorBanner, Page, Panel, buttonClass, inputClass } from "../components/ui";

const ADMIN = "admin";

function PermissionGrid({ modules, selected, onToggle, disabled }) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {Object.entries(modules).map(([module, actions]) => (
        <div key={module} className="flex items-center justify-between rounded-lg border border-gray-800 px-3 py-2">
          <span className="capitalize text-sm">{module}</span>
          <span className="flex gap-3">
            {actions.map((action) => {
              const perm = `${module}.${action}`;
              return (
                <label key={perm} className="flex items-center gap-1 text-xs text-gray-300">
                  <input type="checkbox" disabled={disabled} checked={selected.has(perm)} onChange={() => onToggle(perm)} />
                  {action}
                </label>
              );
            })}
          </span>
        </div>
      ))}
    </div>
  );
}

function RolesTab({ modules, roles, reload, setError }) {
  const [name, setName] = useState("");
  const [newPerms, setNewPerms] = useState(new Set());
  const [editing, setEditing] = useState(null); // role name
  const [editPerms, setEditPerms] = useState(new Set());

  const toggle = (setter) => (perm) =>
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(perm)) next.delete(perm);
      else next.add(perm);
      return next;
    });

  const create = async (e) => {
    e.preventDefault();
    const access = {};
    for (const p of newPerms) {
      const [m, a] = p.split(".");
      (access[m] ||= []).push(a);
    }
    try {
      await api.post("/rbac/", { name: name.trim(), access });
      setName("");
      setNewPerms(new Set());
      reload();
    } catch (err) {
      setError(errorMessage(err, "Could not create role"));
    }
  };

  const save = async (role) => {
    try {
      await api.put(`/rbac/${encodeURIComponent(role)}`, { permissions: [...editPerms] });
      setEditing(null);
      reload();
    } catch (err) {
      setError(errorMessage(err, "Could not update role"));
    }
  };

  const remove = async (role) => {
    if (!window.confirm(`Delete role "${role}"? Users lose its permissions immediately.`)) return;
    try {
      await api.delete(`/rbac/${encodeURIComponent(role)}`);
      reload();
    } catch (err) {
      setError(errorMessage(err, "Could not delete role"));
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <Panel title="Create role" subtitle="Read = view a module and its analytics; write = create/change/delete.">
        <form onSubmit={create} className="space-y-4">
          <input className={`${inputClass} w-full`} required minLength={2} maxLength={60} placeholder="Role name, e.g. warehouse_manager"
            value={name} onChange={(e) => setName(e.target.value)} />
          <PermissionGrid modules={modules} selected={newPerms} onToggle={toggle(setNewPerms)} />
          <button className={buttonClass.primary}>Create role</button>
        </form>
      </Panel>

      <div className="space-y-4">
        {roles.map((role) => {
          const isAdmin = role.name === ADMIN;
          const isEditing = editing === role.name;
          const perms = new Set(role.permissions.map((p) => p.name));
          return (
            <Panel
              key={role.id}
              title={role.name}
              subtitle={isAdmin ? "Built-in: always has every permission" : `${perms.size} permission(s)`}
              action={
                !isAdmin && (
                  <div className="flex gap-2">
                    {isEditing ? (
                      <>
                        <button className={buttonClass.primary} onClick={() => save(role.name)}>Save</button>
                        <button className={buttonClass.small} onClick={() => setEditing(null)}>Cancel</button>
                      </>
                    ) : (
                      <button className={buttonClass.small} onClick={() => { setEditing(role.name); setEditPerms(perms); }}>
                        Edit
                      </button>
                    )}
                    <button className={buttonClass.danger} onClick={() => remove(role.name)}>Delete</button>
                  </div>
                )
              }
            >
              <PermissionGrid
                modules={modules}
                selected={isEditing ? editPerms : perms}
                onToggle={toggle(setEditPerms)}
                disabled={!isEditing}
              />
            </Panel>
          );
        })}
      </div>
    </div>
  );
}

function UsersTab({ roles, setError }) {
  const { user: me, refreshUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [resetLink, setResetLink] = useState(null); // {username, reset_url, expires_at, emailed}

  const load = useCallback(async () => {
    try {
      setUsers((await api.get("/rbac/users")).data);
    } catch (err) {
      setError(errorMessage(err, "Could not load users"));
    }
  }, [setError]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleRole = async (u, roleName) => {
    const next = u.roles.includes(roleName) ? u.roles.filter((r) => r !== roleName) : [...u.roles, roleName];
    try {
      await api.put(`/rbac/users/${u.id}/roles`, { roles: next });
      await load();
      if (u.id === me.id) refreshUser();
    } catch (err) {
      setError(errorMessage(err, "Could not change roles"));
    }
  };

  const toggleActive = async (u) => {
    try {
      await api.patch(`/rbac/users/${u.id}`, { is_active: !u.is_active });
      load();
    } catch (err) {
      setError(errorMessage(err, "Could not change account status"));
    }
  };

  const createResetLink = async (u) => {
    if (!window.confirm(`Create a one-time password reset link for ${u.username}?`)) return;
    try {
      const res = await api.post(`/rbac/users/${u.id}/reset-link`);
      setResetLink({ username: u.username, ...res.data });
    } catch (err) {
      setError(errorMessage(err, "Could not create reset link"));
    }
  };

  return (
    <>
    {resetLink && (
      <div role="status" className="mb-4 rounded-2xl border border-indigo-500/40 bg-indigo-500/10 p-4 text-sm">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="font-medium">Reset link for {resetLink.username}</p>
            <p className="text-gray-400 text-xs mt-1">
              Works once, expires {new Date(resetLink.expires_at).toLocaleTimeString()}.
              {resetLink.emailed ? " It was also emailed to them." : " Send it to them privately (e.g. chat), not in a public channel."}
            </p>
            <code className="block mt-2 break-all text-indigo-200">{resetLink.reset_url}</code>
          </div>
          <div className="flex gap-2 shrink-0">
            <button className={buttonClass.small} onClick={() => navigator.clipboard?.writeText(resetLink.reset_url)}>Copy</button>
            <button className={buttonClass.small} onClick={() => setResetLink(null)}>Close</button>
          </div>
        </div>
      </div>
    )}
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-800 text-gray-400 text-xs uppercase text-left">
          <tr>
            <th className="p-3">User</th>
            <th className="p-3">Roles</th>
            <th className="p-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-t border-gray-800 align-top">
              <td className="p-3">
                <div className="font-medium">{u.username}{u.id === me.id && <span className="text-gray-500"> (you)</span>}</div>
                <div className="text-xs text-gray-500">{u.email}</div>
              </td>
              <td className="p-3">
                <div className="flex flex-wrap gap-2">
                  {roles.map((r) => (
                    <label key={r.id}
                      className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs cursor-pointer ${
                        u.roles.includes(r.name) ? "border-indigo-500/60 bg-indigo-500/15 text-indigo-200" : "border-gray-700 text-gray-400"
                      }`}>
                      <input type="checkbox" className="sr-only" checked={u.roles.includes(r.name)} onChange={() => toggleRole(u, r.name)} />
                      {r.name}
                    </label>
                  ))}
                  {u.roles.length === 0 && <span className="text-xs text-yellow-300">No role — this user can't see any data</span>}
                </div>
              </td>
              <td className="p-3">
                <button className={u.is_active ? buttonClass.small : buttonClass.primary} disabled={u.id === me.id}
                  onClick={() => toggleActive(u)}>
                  {u.is_active ? "Deactivate" : "Activate"}
                </button>
                {!u.is_active && <div className="text-xs text-red-300 mt-1">Deactivated</div>}
                {u.is_active && u.id !== me.id && (
                  <button className={`${buttonClass.small} mt-2 block`} onClick={() => createResetLink(u)}>
                    Reset password
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </>
  );
}

export default function Roles() {
  const [tab, setTab] = useState("users");
  const [modules, setModules] = useState({});
  const [roles, setRoles] = useState([]);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    try {
      const [catalog, roleRes] = await Promise.all([api.get("/rbac/permissions"), api.get("/rbac/")]);
      setModules(catalog.data.modules);
      setRoles(roleRes.data);
    } catch (err) {
      setError(errorMessage(err, "Could not load roles"));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const tabs = useMemo(() => [["users", "Users"], ["roles", "Roles"]], []);

  return (
    <Page title="Users & Roles" subtitle="Assign roles to users and decide what each role can do.">
      <ErrorBanner message={error} onClose={() => setError("")} />
      <div role="tablist" className="flex mb-6 gap-6 border-b border-gray-800">
        {tabs.map(([id, label]) => (
          <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={`pb-2 ${tab === id ? "border-b-2 border-indigo-500 text-indigo-300" : "text-gray-400"}`}>
            {label}
          </button>
        ))}
      </div>
      {tab === "users" ? (
        <UsersTab roles={roles} setError={setError} />
      ) : (
        <RolesTab modules={modules} roles={roles} reload={reload} setError={setError} />
      )}
    </Page>
  );
}
