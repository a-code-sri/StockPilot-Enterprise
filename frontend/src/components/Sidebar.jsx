import { NavLink, useLocation } from "react-router-dom";
import { useMemo, useState } from "react";

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/roles", label: "RBAC" },
  { to: "/inventory", label: "Inventory" },
  { to: "/accounts", label: "Accounts" },
  { to: "/organization", label: "Organization" },
  { to: "/projects", label: "Projects" },
  { to: "/delivery", label: "Delivery" },
];

const analyticsItems = [
  { to: "/analytics", label: "Analytics Home" },
  { to: "/analytics/inventory", label: "Inventory" },
  { to: "/analytics/accounts", label: "Accounts" },
  { to: "/analytics/organization", label: "Organization" },
  { to: "/analytics/delivery", label: "Delivery" },
];

function SidebarItem({ to, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          "group relative flex items-center gap-3 rounded-xl px-4 py-3 transition",
          "border border-transparent hover:border-indigo-500/30",
          "hover:bg-gradient-to-r hover:from-indigo-500/10 hover:to-purple-500/10",
          isActive ? "bg-white/5 border-indigo-500/30" : "text-gray-200/90",
        ].join(" ")
      }
    >
      <span
        className={[
          "absolute left-0 top-1/2 -translate-y-1/2 h-7 w-1 rounded-full",
          "bg-gradient-to-b from-indigo-400 to-purple-500",
          "opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-2 transition-all duration-200",
        ].join(" ")}
      />
      <span className="h-2.5 w-2.5 rounded-full bg-indigo-400/70 shadow-[0_0_18px_rgba(129,140,248,0.35)]" />
      <span className="font-medium tracking-wide">{label}</span>
      <span className="ml-auto text-gray-400 opacity-0 translate-x-1 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200">
        →
      </span>
    </NavLink>
  );
}

export default function Sidebar() {
  const location = useLocation();
  const isAnalyticsRoute = useMemo(
    () => location.pathname.startsWith("/analytics"),
    [location.pathname]
  );

  const [analyticsOpen, setAnalyticsOpen] = useState(isAnalyticsRoute);

  return (
    <aside className="w-72 bg-gray-950 text-white min-h-screen border-r border-gray-800/80">
      <div className="p-6">
        <div className="rounded-2xl p-[1px] bg-gradient-to-r from-indigo-500/60 to-purple-500/60">
          <div className="rounded-2xl bg-gray-950 px-5 py-4">
            <h2 className="text-lg font-bold bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
              Business OS
            </h2>
            <p className="text-xs text-gray-400 mt-1">Manufacturing Control Panel</p>
          </div>
        </div>

        <nav className="mt-8 space-y-3">
          {navItems.map((it) => (
            <SidebarItem key={it.to} to={it.to} label={it.label} />
          ))}

          {/* Analytics dropdown */}
          <button
            onClick={() => setAnalyticsOpen((v) => !v)}
            className={[
              "w-full mt-2 text-left group relative flex items-center gap-3 rounded-xl px-4 py-3 transition",
              "border border-gray-800 hover:border-indigo-500/30",
              "bg-gray-900/20 hover:bg-gradient-to-r hover:from-indigo-500/10 hover:to-purple-500/10",
            ].join(" ")}
          >
            <span className="h-2.5 w-2.5 rounded-full bg-purple-400/70 shadow-[0_0_18px_rgba(168,85,247,0.30)]" />
            <span className="font-medium tracking-wide">Analytics</span>
            <span className="ml-auto text-gray-400">
              {analyticsOpen ? "▾" : "▸"}
            </span>
          </button>

          {analyticsOpen && (
            <div className="ml-3 pl-3 border-l border-gray-800 space-y-2">
              {analyticsItems.map((a) => (
                <NavLink
                  key={a.to}
                  to={a.to}
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

        <div className="mt-10 text-xs text-gray-500">
          <div className="border-t border-gray-800 pt-4">
            <div className="flex items-center justify-between">
              <span>Status</span>
              <span className="text-emerald-400">Online</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}