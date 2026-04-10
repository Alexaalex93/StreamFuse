import { useMemo, useState } from "react";

type LinePoint = {
  label: string;
  value: number;
};

type LineChartProps = {
  points: LinePoint[];
  valueFormatter?: (value: number) => string;
  lineColorClass?: string;
  yAxisTitle?: string;
  xAxisTitle?: string;
};

type NormalizedPoint = LinePoint & { x: number; y: number };

function buildXTicks(points: LinePoint[]): string[] {
  if (points.length <= 5) {
    return points.map((point) => point.label);
  }

  const indexes = [0, Math.floor(points.length * 0.25), Math.floor(points.length * 0.5), Math.floor(points.length * 0.75), points.length - 1];
  const unique = Array.from(new Set(indexes));
  return unique.map((index) => points[index]?.label ?? "");
}

export function LineChart({
  points,
  valueFormatter,
  lineColorClass = "stroke-cyan-300",
  yAxisTitle,
  xAxisTitle,
}: LineChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const stats = useMemo(() => {
    if (points.length === 0) {
      return {
        normalized: [] as NormalizedPoint[],
        min: 0,
        max: 1,
      };
    }

    const values = points.map((item) => item.value);
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const range = Math.max(max - min, 1);

    const normalized = points.map((item, index) => {
      const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
      const y = 100 - ((item.value - min) / range) * 100;
      return { ...item, x, y };
    });

    return { normalized, min, max };
  }, [points]);

  const path = useMemo(() => {
    if (stats.normalized.length === 0) {
      return "";
    }
    return stats.normalized
      .map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(2)},${point.y.toFixed(2)}`)
      .join(" ");
  }, [stats.normalized]);

  const hoverPoint = hoverIndex != null ? stats.normalized[hoverIndex] : null;

  const yTicks = useMemo(() => {
    const tickValues = [stats.max, stats.min + (stats.max - stats.min) * 0.66, stats.min + (stats.max - stats.min) * 0.33, stats.min];
    return tickValues.map((value) => (valueFormatter ? valueFormatter(value) : String(Math.round(value))));
  }, [stats.max, stats.min, valueFormatter]);

  const xTicks = useMemo(() => buildXTicks(points), [points]);

  return (
    <div className="relative">
      <div className="grid grid-cols-[52px_1fr] gap-2">
        <div className="flex h-48 flex-col justify-between text-[11px] text-fg-muted">
          {yTicks.map((tick, index) => (
            <span key={`${tick}-${index}`} className="truncate">{tick}</span>
          ))}
        </div>

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

          {stats.normalized.map((point, index) => (
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
      </div>

      <div className="mt-1 grid grid-cols-[52px_1fr] gap-2">
        <span className="text-[11px] uppercase tracking-[0.08em] text-fg-muted">{yAxisTitle || "Y"}</span>
        <div className="flex justify-between text-[11px] text-fg-muted">
          {xTicks.map((label, index) => (
            <span key={`${label}-${index}`} className="truncate">{label}</span>
          ))}
        </div>
      </div>

      {xAxisTitle ? <p className="mt-1 text-[11px] uppercase tracking-[0.08em] text-fg-muted">{xAxisTitle}</p> : null}

      {hoverPoint ? (
        <div className="pointer-events-none absolute right-2 top-2 max-w-[180px] rounded-lg border border-white/15 bg-[#050b16] px-2 py-1 text-xs text-fg">
          <p className="truncate">{hoverPoint.label}</p>
          <p className="text-cyan-200">{valueFormatter ? valueFormatter(hoverPoint.value) : hoverPoint.value}</p>
        </div>
      ) : null}
    </div>
  );
}
