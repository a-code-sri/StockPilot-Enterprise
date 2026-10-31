import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useRealtime } from "../realtime/RealtimeProvider";

// `permission: null` = visible to every signed-in user.
const navItems = [
  { to: "/dashboard", label: "Dashboard", permission: null },
  { to: "/assistant", label: "AI Assistant", permission: "ai.use" },
  { to: "/inventory", label: "Inventory", permission: "inventory.read" },
  { to: "/accounts", label: "Accounts", permission: "accounts.read" },
  { to: "/organization", label: "Organization", permission: "organization.read" },
  { to: "/projects", label: "Projects", permission: "projects.read" },
  { to: "/delivery", label: "Delivery", permission: "delivery.read" },
  { to: "/business", label: "Business Profile", permission: null },
  { to: "/roles", label: "Users & Roles", permission: "rbac.manage" },
];

const analyticsItems = [
  { to: "/analytics", label: "Analytics Home", permission: null },
  { to: "/analytics/inventory", label: "Inventory", permission: "inventory.read" },
  { to: "/analytics/accounts", label: "Accounts", permission: "accounts.read" },
  { to: "/analytics/organization", label: "Organization", permission: "organization.read" },
  { to: "/analytics/delivery", label: "Delivery", permission: "delivery.read" },
  { to: "/analytics/projects", label: "Projects", permission: "projects.read" },
];

const STATUS_STYLE = {
  connected: ["text-emerald-400", "Live"],
  connecting: ["text-yellow-300", "Connecting"],
  disconnected: ["text-gray-400", "Offline"],
  unauthenticated: ["text-red-300", "Signed out"],
};

function SidebarItem({ to, label }) {
  return (
    <NavLink
      to={to}
      end={to === "/analytics"}
      className={({ isActive }) =>
        [
          "group relative flex items-center gap-3 rounded-xl px-4 py-2.5 transition",
          "border border-transparent hover:border-indigo-500/30",
          "hover:bg-gradient-to-r hover:from-indigo-500/10 hover:to-purple-500/10",
          isActive ? "bg-white/5 border-indigo-500/30" : "text-gray-200/90",
        ].join(" ")
      }
    >
      <span className="h-2.5 w-2.5 rounded-full bg-indigo-400/70 shadow-[0_0_18px_rgba(129,140,248,0.35)]" />
      <span className="font-medium tracking-wide">{label}</span>
    </NavLink>
  );
}

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, can, logout } = useAuth();
  const { status } = useRealtime();
  const [analyticsOpen, setAnalyticsOpen] = useState(location.pathname.startsWith("/analytics"));

  const visible = (it) => !it.permission || can(it.permission);
  const [statusClass, statusLabel] = STATUS_STYLE[status] || STATUS_STYLE.disconnected;

  const handleLogout = () => {
    logout();
    navigate("/", { replace: true });
  };

  return (
    <aside className="w-72 shrink-0 bg-gray-950 text-white min-h-screen border-r border-gray-800/80">
      <div className="p-6">
        <div className="rounded-2xl p-[1px] bg-gradient-to-r from-indigo-500/60 to-purple-500/60">
          <div className="rounded-2xl bg-gray-950 px-5 py-4">
            <h2 className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
              StockPilot
            </h2>
            <p className="text-xs text-gray-400 mt-1">Manufacturing Control Panel</p>
          </div>
        </div>

        <nav className="mt-8 space-y-2">
          {navItems.filter(visible).map((it) => (
            <SidebarItem key={it.to} to={it.to} label={it.label} />
          ))}

          <button
            type="button"
            onClick={() => setAnalyticsOpen((v) => !v)}
            aria-expanded={analyticsOpen}
            className="w-full mt-2 text-left flex items-center gap-3 rounded-xl px-4 py-2.5 transition border border-gray-800 hover:border-indigo-500/30 bg-gray-900/20"
          >
            <span className="h-2.5 w-2.5 rounded-full bg-purple-400/70" />
            <span className="font-medium tracking-wide">Analytics</span>
            <span className="ml-auto text-gray-400">{analyticsOpen ? "▾" : "▸"}</span>
          </button>

          {analyticsOpen && (
            <div className="ml-3 pl-3 border-l border-gray-800 space-y-1">
              {analyticsItems.filter(visible).map((a) => (
                <NavLink
                  key={a.to}
                  to={a.to}
                  end
                  className={({ isActive }) =>
                    [
                      "block rounded-xl px-4 py-2 text-sm transition",
                      isActive
                        ? "bg-indigo-500/10 border border-indigo-500/20 text-indigo-200"
                        : "text-gray-300 hover:text-indigo-200 hover:bg-gray-900/30",
                    ].join(" ")
                  }
                >
                  {a.label}
                </NavLink>
              ))}
            </div>
          )}
        </nav>

        <div className="mt-10 text-xs text-gray-400 border-t border-gray-800 pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <span>Realtime</span>
            <span className={statusClass}>{statusLabel}</span>
          </div>
          {user && (
            <div className="flex items-center justify-between gap-2">
              <span className="truncate" title={user.email}>
                {user.username}
                <span className="text-gray-500"> · {user.roles.map((r) => r.name).join(", ") || "no role"}</span>
              </span>
              <button
                type="button"
                onClick={handleLogout}
                className="shrink-0 rounded-lg border border-gray-700 px-2 py-1 text-gray-300 hover:border-red-500/50 hover:text-red-300"
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
