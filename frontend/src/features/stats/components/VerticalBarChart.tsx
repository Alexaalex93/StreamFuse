import { useMemo, useState } from "react";

type BarPoint = {
  label: string;
  value: number;
};

type VerticalBarChartProps = {
  points: BarPoint[];
  valueFormatter?: (value: number) => string;
  yAxisTitle?: string;
  xAxisTitle?: string;
  barColor?: string;
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

export function VerticalBarChart({
  points,
  valueFormatter,
  yAxisTitle,
  xAxisTitle,
  barColor = "#22d3ee",
  maxXTicks = 12,
}: VerticalBarChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const safePoints = useMemo(
    () => points.map((p) => ({ label: p.label, value: Number.isFinite(p.value) ? p.value : 0 })),
    [points],
  );

  const max = Math.max(...safePoints.map((p) => p.value), 1);
  const yTicks = [max, max * 0.66, max * 0.33, 0];
  const tickSet = useMemo(() => buildTickSet(safePoints.length, maxXTicks), [safePoints.length, maxXTicks]);
  const hover = hoveredIndex != null ? safePoints[hoveredIndex] : null;
  const hoverLeft = hoveredIndex != null && safePoints.length > 0
    ? `${((hoveredIndex + 0.5) / safePoints.length) * 100}%`
    : "50%";

  return (
    <div className="space-y-2">
      {yAxisTitle ? <p className="text-[11px] uppercase tracking-[0.08em] text-fg-muted">{yAxisTitle}</p> : null}

      <div className="grid grid-cols-[72px_1fr] gap-2">
        <div className="flex h-52 flex-col justify-between text-[11px] text-fg-muted">
          {yTicks.map((tick, index) => (
            <span key={`${tick}-${index}`} className="truncate">
              {valueFormatter ? valueFormatter(tick) : Math.round(tick)}
            </span>
          ))}
        </div>

        <div className="relative h-52 overflow-hidden rounded-xl border border-white/10 bg-panel/40">
          <div className="absolute inset-0">
            {[20, 40, 60, 80].map((line) => (
              <div key={line} className="absolute left-0 right-0 border-t border-white/10" style={{ top: `${line}%` }} />
            ))}
          </div>

          <div className="absolute bottom-0 left-0 right-0 grid h-full grid-flow-col auto-cols-fr gap-1 px-2 pb-1">
            {safePoints.map((point, index) => {
              const ratio = point.value / max;
              const height = point.value > 0 ? Math.max(ratio * 100, 2) : 0;
              return (
                <div key={`${point.label}-${index}`} className="flex h-full items-end justify-center">
                  <div
                    className="w-[78%] rounded-t-sm transition-opacity"
                    style={{
                      height: `${height}%`,
                      backgroundColor: barColor,
                      opacity: hoveredIndex == null || hoveredIndex === index ? 1 : 0.65,
                    }}
                    onMouseEnter={() => setHoveredIndex(index)}
                    onMouseLeave={() => setHoveredIndex(null)}
                    title={`${point.label}: ${valueFormatter ? valueFormatter(point.value) : point.value}`}
                  />
                </div>
              );
            })}
          </div>

          {hover ? (
            <div
              className="pointer-events-none absolute top-2 z-10 max-w-[240px] -translate-x-1/2 rounded-lg border border-white/15 bg-[#050b16] px-2 py-1 text-xs text-fg"
              style={{ left: hoverLeft }}
            >
              <p className="truncate text-fg-muted">{hover.label}</p>
              <p className="text-cyan-200">{valueFormatter ? valueFormatter(hover.value) : hover.value}</p>
            </div>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-[72px_1fr] gap-2">
        <span />
        <div className="grid grid-flow-col auto-cols-fr gap-1 px-2">
          {safePoints.map((point, index) => (
            <span key={`${point.label}-x-${index}`} className="truncate text-center text-[11px] text-fg-muted" title={point.label}>
              {tickSet.has(index) ? point.label : ""}
            </span>
          ))}
        </div>
      </div>

      {xAxisTitle ? <p className="text-center text-[11px] uppercase tracking-[0.08em] text-fg-muted">{xAxisTitle}</p> : null}
    </div>
  );
}
