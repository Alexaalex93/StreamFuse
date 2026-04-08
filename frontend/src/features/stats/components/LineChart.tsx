import { useMemo, useState } from "react";

type LinePoint = {
  label: string;
  value: number;
};

type LineChartProps = {
  points: LinePoint[];
  valueFormatter?: (value: number) => string;
  lineColorClass?: string;
};

export function LineChart({ points, valueFormatter, lineColorClass = "stroke-cyan-300" }: LineChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const normalized = useMemo(() => {
    if (points.length === 0) {
      return [] as Array<LinePoint & { x: number; y: number }>;
    }

    const values = points.map((item) => item.value);
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const range = Math.max(max - min, 1);

    return points.map((item, index) => {
      const x = points.length === 1 ? 0 : (index / (points.length - 1)) * 100;
      const y = 100 - ((item.value - min) / range) * 100;
      return { ...item, x, y };
    });
  }, [points]);

  const path = useMemo(() => {
    if (normalized.length === 0) {
      return "";
    }
    return normalized
      .map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.y.toFixed(2)}`)
      .join(" ");
  }, [normalized]);

  const hoverPoint = hoverIndex != null ? normalized[hoverIndex] : null;

  return (
    <div className="relative">
      <svg viewBox="0 0 100 100" className="h-48 w-full overflow-visible" preserveAspectRatio="none">
        <defs>
          <linearGradient id="areaGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgba(56,189,248,0.35)" />
            <stop offset="100%" stopColor="rgba(56,189,248,0.02)" />
          </linearGradient>
        </defs>

        <g className="stroke-white/15" strokeWidth="0.4">
          <line x1="0" y1="20" x2="100" y2="20" />
          <line x1="0" y1="40" x2="100" y2="40" />
          <line x1="0" y1="60" x2="100" y2="60" />
          <line x1="0" y1="80" x2="100" y2="80" />
        </g>

        {path ? <path d={`${path} L100,100 L0,100 Z`} fill="url(#areaGradient)" /> : null}
        {path ? <path d={path} className={`${lineColorClass} fill-none`} strokeWidth="1.5" /> : null}

        {normalized.map((point, index) => (
          <g key={`${point.label}-${index}`}>
            <circle
              cx={point.x}
              cy={point.y}
              r={hoverIndex === index ? 1.5 : 1}
              className="fill-cyan-200 transition"
              onMouseEnter={() => setHoverIndex(index)}
              onMouseLeave={() => setHoverIndex(null)}
            />
          </g>
        ))}
      </svg>

      <div className="mt-1 flex justify-between text-[11px] text-fg-muted">
        <span>{points[0]?.label ?? ""}</span>
        <span>{points[points.length - 1]?.label ?? ""}</span>
      </div>

      {hoverPoint ? (
        <div className="pointer-events-none absolute right-2 top-2 rounded-lg border border-white/15 bg-[#050b16] px-2 py-1 text-xs text-fg">
          <p>{hoverPoint.label}</p>
          <p className="text-cyan-200">{valueFormatter ? valueFormatter(hoverPoint.value) : hoverPoint.value}</p>
        </div>
      ) : null}
    </div>
  );
}
