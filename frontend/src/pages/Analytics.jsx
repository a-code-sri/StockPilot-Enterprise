import { useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar";

export default function Analytics() {
  const navigate = useNavigate();

  const cards = [
    {
      title: "Inventory Analytics",
      desc: "Dead stock, stockout prediction, reorder suggestions, consumption & orders trends.",
      to: "/analytics/inventory",
      accent: "from-indigo-500/20 to-purple-500/10",
      border: "border-indigo-500/20",
    },
    {
      title: "Accounts Analytics",
      desc: "Income vs expenses, category distributions, liquidity score, top sources/targets.",
      to: "/analytics/accounts",
      accent: "from-emerald-500/15 to-indigo-500/10",
      border: "border-emerald-500/20",
    },
    {
      title: "Delivery Analytics (soon)",
      desc: "SLA, funnel bottlenecks, failure trends.",
      to: "/analytics",
      disabled: true,
      accent: "from-gray-800/50 to-gray-900/10",
      border: "border-gray-800",
    },
    {
      title: "Organization Analytics",
      desc: "Department share, salary distribution, top executive overview.",
      to: "/analytics/organization",
      accent: "from-purple-500/15 to-indigo-500/10",
      border: "border-purple-500/20",
    },
    {
    title: "Delivery Analytics",
    desc: "Moving averages, most ordered items, status distribution, peak delivery time.",
    to: "/analytics/delivery",
    accent: "from-blue-500/15 to-indigo-500/10",
    border: "border-blue-500/20",
  },
  ];

  return (
    <div className="flex bg-gray-950 text-gray-200 min-h-screen">
      <Sidebar />
      <div className="flex-1 p-10">
        <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
          Analytics
        </h1>
        <p className="text-gray-400 mb-8">Choose a module to explore deeper insights.</p>

        <div className="grid grid-cols-12 gap-6">
          {cards.map((c) => (
            <button
              key={c.title}
              onClick={() => !c.disabled && navigate(c.to)}
              className={[
                "col-span-12 lg:col-span-6 text-left rounded-2xl p-6 transition",
                "bg-gradient-to-br",
                c.accent,
                "border",
                c.border,
                c.disabled
                  ? "opacity-60 cursor-not-allowed"
                  : "hover:border-indigo-500/40 hover:shadow-[0_0_30px_rgba(129,140,248,0.12)]",
              ].join(" ")}
              disabled={c.disabled}
            >
              <div className="text-lg font-semibold">{c.title}</div>
              <div className="text-sm text-gray-400 mt-2">{c.desc}</div>
              {!c.disabled && <div className="text-indigo-300 mt-4 text-sm">Open →</div>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}