import { useMemo, useRef, useState } from "react";

type AreaPoint = { label: string; value: number };

type AreaChartProps = {
  points: AreaPoint[];
  valueFormatter?: (value: number) => string;
  yAxisTitle?: string;
  xAxisTitle?: string;
  color?: string;
  maxXTicks?: number;
};

function buildTickSet(total: number, maxTicks: number): Set<number> {
  if (total <= 0) return new Set<number>();
  if (total <= maxTicks) return new Set(Array.from({ length: total }, (_, i) => i));
  const step = Math.ceil(total / maxTicks);
  const values: number[] = [];
  for (let i = 0; i < total; i += step) values.push(i);
  if (values[values.length - 1] !== total - 1) values.push(total - 1);
  return new Set(values);
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function AreaChart({
  points,
  valueFormatter,
  yAxisTitle,
  xAxisTitle,
  color = "#22d3ee",
  maxXTicks = 12,
}: AreaChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const chartRef = useRef<HTMLDivElement | null>(null);

  const safePoints = useMemo(
    () => points.map((p) => ({ label: p.label, value: Number.isFinite(p.value) ? p.value : 0 })),
    [points],
  );

  const max = Math.max(...safePoints.map((p) => p.value), 1);
  const yTicks = [max, max * 0.66, max * 0.33, 0];
  const tickSet = useMemo(() => buildTickSet(safePoints.length, maxXTicks), [safePoints.length, maxXTicks]);

  const coords = useMemo(
    () =>
      safePoints.map((p, i) => ({
        ...p,
        x: safePoints.length === 1 ? 50 : (i / (safePoints.length - 1)) * 100,
        y: max > 0 ? 100 - (p.value / max) * 100 : 100,
      })),
    [safePoints, max],
  );

  const linePath = coords.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
  const areaPath =
    coords.length > 0
      ? `M${coords[0].x.toFixed(2)},100 ${coords.map((p) => `L${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ")} L${coords[coords.length - 1].x.toFixed(2)},100 Z`
      : "";

  const hoverX =
    hoverIndex != null && coords.length > 1
      ? (hoverIndex / (coords.length - 1)) * 100
      : coords.length === 1
        ? 50
        : null;

  const hover = hoverIndex != null ? safePoints[hoverIndex] : null;
  const gradientId = `area-grad-${color.replace("#", "")}`;

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!chartRef.current || coords.length === 0) return;
    const rect = chartRef.current.getBoundingClientRect();
    const x = clamp(e.clientX - rect.left, 0, rect.width);
    const idx =
      coords.length === 1
        ? 0
        : clamp(Math.round((x / rect.width) * (coords.length - 1)), 0, coords.length - 1);
    setHoverIndex(idx);
  };

  return (
    <div className="space-y-2">
      {yAxisTitle ? <p className="text-[11px] uppercase tracking-[0.08em] text-fg-muted">{yAxisTitle}</p> : null}

      <div className="grid grid-cols-[72px_1fr] gap-2">
        <div className="flex h-52 flex-col justify-between text-[11px] text-fg-muted">
          {yTicks.map((tick, i) => (
            <span key={i} className="truncate">
              {valueFormatter ? valueFormatter(tick) : Math.round(tick)}
            </span>
          ))}
        </div>

        <div
          ref={chartRef}
          className="relative h-52 overflow-hidden rounded-xl border border-white/10 bg-panel/40"
          onMouseMove={onMouseMove}
          onMouseLeave={() => setHoverIndex(null)}
        >
          <svg
            viewBox="0 0 100 100"
            className="h-full w-full"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity="0.22" />
                <stop offset="100%" stopColor={color} stopOpacity="0.02" />
              </linearGradient>
            </defs>

            <g stroke="rgba(255,255,255,0.08)" strokeWidth="0.5" fill="none">
              {[20, 40, 60, 80].map((y) => (
                <line key={y} x1="0" y1={y} x2="100" y2={y} />
              ))}
            </g>

            {areaPath ? <path d={areaPath} fill={`url(#${gradientId})`} /> : null}
            {linePath ? (
              <path
                d={linePath}
                fill="none"
                stroke={color}
                strokeWidth="0.55"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ) : null}

            {hoverX != null ? (
              <line
                x1={hoverX}
                y1="0"
                x2={hoverX}
                y2="100"
                stroke="rgba(165,243,252,0.55)"
                strokeWidth="0.5"
              />
            ) : null}

            {hoverIndex != null && coords[hoverIndex] ? (
              <circle
                cx={coords[hoverIndex].x}
                cy={coords[hoverIndex].y}
                r="1.1"
                fill={color}
              />
            ) : null}
          </svg>

          {hover && hoverX != null ? (
            <div
              className="pointer-events-none absolute top-2 z-10 max-w-[200px] -translate-x-1/2 rounded-lg border border-white/15 bg-[#050b16] px-2 py-1 text-xs text-fg"
              style={{ left: `${hoverX}%` }}
            >
              <p className="truncate text-fg-muted">{hover.label}</p>
              <p className="text-cyan-200">
                {valueFormatter ? valueFormatter(hover.value) : hover.value}
              </p>
            </div>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-[72px_1fr] gap-2">
        <span />
        <div className="grid grid-flow-col auto-cols-fr gap-1 px-2">
          {safePoints.map((point, index) => (
            <span
              key={`${point.label}-x-${index}`}
              className="truncate text-center text-[11px] text-fg-muted"
              title={point.label}
            >
              {tickSet.has(index) ? point.label : ""}
            </span>
          ))}
        </div>
      </div>

      {xAxisTitle ? (
        <p className="text-center text-[11px] uppercase tracking-[0.08em] text-fg-muted">{xAxisTitle}</p>
      ) : null}
    </div>
  );
}
