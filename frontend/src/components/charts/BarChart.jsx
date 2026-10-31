import React, { useMemo } from "react";

export default function BarChart({
  data = [],             // [{ label: "2026-08-01", value: 10 }]
  width = 700,
  height = 220,
  barColor = "rgba(168,85,247,0.65)", // purple-ish
  valueKey = "value",
  labelKey = "label",
}) {
  const padding = 28;

  const bars = useMemo(() => {
    if (!data.length) return [];

    const values = data.map((d) => Number(d[valueKey] ?? 0));
    const max = Math.max(...values, 1);

    const usableW = width - padding * 2;
    const usableH = height - padding * 2;

    const barW = usableW / data.length;

    return data.map((d, i) => {
      const v = Number(d[valueKey] ?? 0);
      const h = (v / max) * usableH;
      const x = padding + i * barW + barW * 0.15;
      const y = height - padding - h;
      const w = barW * 0.7;
      return { x, y, w, h, v, label: d[labelKey] };
    });
  }, [data, width, height, valueKey, labelKey]);

  if (!data.length) return <div className="text-gray-500 text-sm">No chart data available.</div>;

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="block">
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(148,163,184,0.25)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="rgba(148,163,184,0.25)" />

      {bars.map((b, idx) => (
        <rect
          key={idx}
          x={b.x}
          y={b.y}
          width={b.w}
          height={b.h}
          rx="6"
          fill={barColor}
        />
      ))}
    </svg>
  );
}