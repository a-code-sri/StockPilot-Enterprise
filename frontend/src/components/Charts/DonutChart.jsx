import React, { useMemo } from "react";

function polarToCartesian(cx, cy, r, angleDeg) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180.0;
  return {
    x: cx + r * Math.cos(angleRad),
    y: cy + r * Math.sin(angleRad),
  };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
}

export default function DonutChart({
  income = 0,
  expenses = 0,
  size = 220,
  thickness = 22,
}) {
  const total = Math.max(0, Number(income) + Number(expenses));

  const { incomeAngle, expenseAngle } = useMemo(() => {
    if (total <= 0) return { incomeAngle: 0, expenseAngle: 0 };
    const incomeAngle = (Number(income) / total) * 360;
    const expenseAngle = (Number(expenses) / total) * 360;
    return { incomeAngle, expenseAngle };
  }, [income, expenses, total]);

  const cx = size / 2;
  const cy = size / 2;
  const r = (size - thickness) / 2;

  // Start at 0° and draw income first, then expenses
  const incomeStart = 0;
  const incomeEnd = incomeAngle;

  const expenseStart = incomeEnd;
  const expenseEnd = incomeEnd + expenseAngle;

  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} className="block">
        {/* background ring */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="rgba(148,163,184,0.20)"
          strokeWidth={thickness}
        />

        {total > 0 && incomeAngle > 0 && (
          <path
            d={describeArc(cx, cy, r, incomeStart, incomeEnd)}
            fill="none"
            stroke="rgba(52,211,153,0.85)" // emerald
            strokeWidth={thickness}
            strokeLinecap="round"
          />
        )}

        {total > 0 && expenseAngle > 0 && (
          <path
            d={describeArc(cx, cy, r, expenseStart, expenseEnd)}
            fill="none"
            stroke="rgba(248,113,113,0.85)" // red
            strokeWidth={thickness}
            strokeLinecap="round"
          />
        )}

        {/* center text */}
        <text x={cx} y={cy - 4} textAnchor="middle" fill="rgba(229,231,235,1)" fontSize="14" fontWeight="700">
          Net
        </text>
        <text x={cx} y={cy + 18} textAnchor="middle" fill="rgba(129,140,248,1)" fontSize="16" fontWeight="800">
          ${Math.round(Number(income) - Number(expenses))}
        </text>
      </svg>

      <div className="space-y-3">
        <LegendRow color="bg-emerald-400" label="Income" value={income} />
        <LegendRow color="bg-red-400" label="Expenses" value={expenses} />
        <div className="text-xs text-gray-500">Window total: ${Math.round(total)}</div>
      </div>
    </div>
  );
}

function LegendRow({ color, label, value }) {
  return (
    <div className="flex items-center justify-between gap-6">
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
        <span className="text-sm text-gray-300">{label}</span>
      </div>
      <span className="text-sm font-semibold text-gray-200">${Math.round(Number(value) || 0)}</span>
    </div>
  );
}