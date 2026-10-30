import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Page } from "../components/ui";

const CARDS = [
  {
    title: "Inventory",
    desc: "Alerts, reorder suggestions, stock-out forecast, consumption trends and unusual usage.",
    to: "/analytics/inventory",
    permission: "inventory.read",
    accent: "from-indigo-500/20 to-purple-500/10 border-indigo-500/20",
  },
  {
    title: "Accounts",
    desc: "Income vs expenses, category mix, liquidity score, top counterparties and unusual transactions.",
    to: "/analytics/accounts",
    permission: "accounts.read",
    accent: "from-emerald-500/15 to-indigo-500/10 border-emerald-500/20",
  },
  {
    title: "Delivery",
    desc: "Moving averages, most ordered items, status breakdown and peak delivery hours.",
    to: "/analytics/delivery",
    permission: "delivery.read",
    accent: "from-sky-500/15 to-indigo-500/10 border-sky-500/20",
  },
  {
    title: "Organization",
    desc: "Department share, salary distribution and head of organisation.",
    to: "/analytics/organization",
    permission: "organization.read",
    accent: "from-purple-500/15 to-indigo-500/10 border-purple-500/20",
  },
  {
    title: "Projects",
    desc: "Portfolio risk, schedule slack and critical paths across projects.",
    to: "/analytics/projects",
    permission: "projects.read",
    accent: "from-amber-500/15 to-indigo-500/10 border-amber-500/20",
  },
];

export default function Analytics() {
  const { can } = useAuth();
  const cards = CARDS.filter((c) => can(c.permission));

  return (
    <Page title="Analytics" subtitle="Live dashboards, updated automatically as data changes.">
      {cards.length === 0 && (
        <p className="text-gray-400">You don't have access to any analytics yet. Ask an administrator for a role.</p>
      )}
      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((c) => (
          <Link key={c.to} to={c.to}
            className={`block rounded-2xl border bg-gradient-to-br p-6 transition hover:-translate-y-0.5 hover:border-indigo-400/40 ${c.accent}`}>
            <h2 className="text-lg font-semibold">{c.title}</h2>
            <p className="text-sm text-gray-400 mt-2">{c.desc}</p>
            <span className="inline-block mt-4 text-sm text-indigo-300">Open →</span>
          </Link>
        ))}
      </div>
    </Page>
  );
}
