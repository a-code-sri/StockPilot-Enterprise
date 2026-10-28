import React, { useMemo } from "react";

/**
 * bins: array length N+1 (edges)
 * counts: array length N
 * Example:
 *  bins = [0, 10, 20, 30]
 *  counts = [2, 5, 1]
 */
export default function HistogramChart({
  bins = [],
  counts = [],
  width = 720,
  height = 240,
}) {
  const padding = 28;

  const bars = useMemo(() => {
    if (!bins?.length || !counts?.length) return [];

    const maxC = Math.max(...counts, 1);
    const n = counts.length;

    const usableW = width - padding * 2;
    const usableH = height - padding * 2;
    const barW = usableW / n;

    return counts.map((c, i) => {
      const h = (c / maxC) * usableH;
      const x = padding + i * barW + barW * 0.12;
      const y = height - padding - h;
      const w = barW * 0.76;

      const low = bins[i];
      const high = bins[i + 1];
      const label = `${low}–${high}`;

      return { x, y, w, h, c, label };
    });
  }, [bins, counts, width, height]);

  if (!bars.length) {
    return <div className="text-gray-500 text-sm">No histogram data.</div>;
  }

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="block">
      <line
        x1={padding}
        y1={height - padding}
        x2={width - padding}
        y2={height - padding}
        stroke="rgba(148,163,184,0.25)"
      />
      <line
        x1={padding}
        y1={padding}
        x2={padding}
        y2={height - padding}
        stroke="rgba(148,163,184,0.25)"
      />

      {bars.map((b, idx) => (
        <g key={idx}>
          <rect
            x={b.x}
            y={b.y}
            width={b.w}
            height={b.h}
            rx="6"
            fill="rgba(129,140,248,0.55)"
          />
        </g>
      ))}
    </svg>
  );
}