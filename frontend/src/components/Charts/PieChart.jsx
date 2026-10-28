import React, { useMemo } from "react";

function polarToCartesian(cx, cy, r, angleDeg) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180.0;
  return { x: cx + r * Math.cos(angleRad), y: cy + r * Math.sin(angleRad) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
}

const PALETTE = [
  "rgba(129,140,248,0.90)", // indigo
  "rgba(168,85,247,0.85)",  // purple
  "rgba(52,211,153,0.85)",  // emerald
  "rgba(248,113,113,0.85)", // red
  "rgba(251,191,36,0.85)",  // amber
  "rgba(59,130,246,0.85)",  // blue
  "rgba(244,114,182,0.85)", // pink
];

export default function PieChart({
  data = [],               // [{ label, value }]
  size = 240,
  thickness = 26,          // donut thickness
  centerLabel = "Total",
  centerValue = "",
}) {
  const total = useMemo(
    () => data.reduce((sum, d) => sum + Number(d.value || 0), 0),
    [data]
  );

  const cx = size / 2;
  const cy = size / 2;
  const r = (size - thickness) / 2;

  const slices = useMemo(() => {
    if (!data.length || total <= 0) return [];

    let start = 0;
    return data.map((d, idx) => {
      const v = Number(d.value || 0);
      const angle = (v / total) * 360;
      const end = start + angle;
      const slice = {
        label: d.label,
        value: v,
        start,
        end,
        color: PALETTE[idx % PALETTE.length],
      };
      start = end;
      return slice;
    });
  }, [data, total]);

  if (!data.length) {
    return <div className="text-gray-500 text-sm">No data.</div>;
  }

  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg width={size} height={size} className="block">
        {/* background ring */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="rgba(148,163,184,0.18)"
          strokeWidth={thickness}
        />

        {slices.map((s, i) => (
          <path
            key={i}
            d={describeArc(cx, cy, r, s.start, s.end)}
            fill="none"
            stroke={s.color}
            strokeWidth={thickness}
            strokeLinecap="round"
          />
        ))}

        <text
          x={cx}
          y={cy - 6}
          textAnchor="middle"
          fill="rgba(229,231,235,1)"
          fontSize="13"
          fontWeight="700"
        >
          {centerLabel}
        </text>
        <text
          x={cx}
          y={cy + 16}
          textAnchor="middle"
          fill="rgba(129,140,248,1)"
          fontSize="16"
          fontWeight="800"
        >
          {centerValue || total}
        </text>
      </svg>

      <div className="space-y-2">
        {slices.map((s, i) => (
          <div key={i} className="flex items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: s.color }}
              />
              <span className="text-sm text-gray-300">{s.label}</span>
            </div>
            <span className="text-sm font-semibold text-gray-200">
              {s.value}
            </span>
          </div>
        ))}
        <div className="text-xs text-gray-500 pt-1">Total: {total}</div>
      </div>
    </div>
  );
}