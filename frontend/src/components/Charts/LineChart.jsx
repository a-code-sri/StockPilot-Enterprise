import React, { useMemo } from "react";

export default function LineChart({
  data = [],              // [{ label: "2026-08-01", value: 10 }]
  width = 700,
  height = 220,
  stroke = "#818cf8",     // indigo-400
  fill = "rgba(129,140,248,0.12)",
  valueKey = "value",
  labelKey = "label",
}) {
  const padding = 28;

  const { points, areaPoints, minV, maxV } = useMemo(() => {
    if (!data.length) return { points: "", areaPoints: "", minV: 0, maxV: 0 };

    const values = data.map((d) => Number(d[valueKey] ?? 0));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;

    const xStep = (width - padding * 2) / Math.max(1, data.length - 1);

    const coords = data.map((d, i) => {
      const v = Number(d[valueKey] ?? 0);
      const x = padding + i * xStep;
      const y = height - padding - ((v - min) / span) * (height - padding * 2);
      return { x, y, v, label: d[labelKey] };
    });

    const poly = coords.map((c) => `${c.x},${c.y}`).join(" ");
    const area = [
      `${coords[0].x},${height - padding}`,
      ...coords.map((c) => `${c.x},${c.y}`),
      `${coords[coords.length - 1].x},${height - padding}`,
    ].join(" ");

    return { points: poly, areaPoints: area, minV: min, maxV: max };
  }, [data, width, height, valueKey, labelKey]);

  if (!data.length) {
    return (
      <div className="text-gray-500 text-sm">No chart data available.</div>
    );
  }

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="block">
      {/* grid */}
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(148,163,184,0.25)" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="rgba(148,163,184,0.25)" />

      {/* min/max labels */}
      <text x={padding} y={padding - 8} fill="rgba(148,163,184,0.8)" fontSize="10">
        {maxV.toFixed(1)}
      </text>
      <text x={padding} y={height - 10} fill="rgba(148,163,184,0.8)" fontSize="10">
        {minV.toFixed(1)}
      </text>

      {/* area fill */}
      <polygon points={areaPoints} fill={fill} />

      {/* line */}
      <polyline
        points={points}
        fill="none"
        stroke={stroke}
        strokeWidth="2.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}