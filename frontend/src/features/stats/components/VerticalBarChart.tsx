type BarPoint = {
  label: string;
  value: number;
};

type VerticalBarChartProps = {
  points: BarPoint[];
  valueFormatter?: (value: number) => string;
  yAxisTitle?: string;
  xAxisTitle?: string;
  barClassName?: string;
  maxXTicks?: number;
};

function buildTicks(points: BarPoint[], maxTicks: number): BarPoint[] {
  if (points.length <= maxTicks) return points;
  const step = Math.ceil(points.length / maxTicks);
  return points.filter((_, index) => index % step === 0 || index === points.length - 1);
}

export function VerticalBarChart({
  points,
  valueFormatter,
  yAxisTitle,
  xAxisTitle,
  barClassName = "from-cyan-400 to-cyan-200",
  maxXTicks = 12,
}: VerticalBarChartProps) {
  const max = Math.max(...points.map((p) => p.value), 1);
  const yTicks = [max, max * 0.66, max * 0.33, 0];
  const xTicks = buildTicks(points, maxXTicks);

  return (
    <div className="space-y-2">
      {yAxisTitle ? <p className="text-[11px] uppercase tracking-[0.08em] text-fg-muted">{yAxisTitle}</p> : null}
      <div className="grid grid-cols-[70px_1fr] gap-2">
        <div className="flex h-52 flex-col justify-between text-[11px] text-fg-muted">
          {yTicks.map((tick, index) => (
            <span key={`${tick}-${index}`} className="truncate">
              {valueFormatter ? valueFormatter(tick) : Math.round(tick)}
            </span>
          ))}
        </div>

        <div className="relative h-52 rounded-xl border border-white/10 bg-panel/40 px-2 pb-8 pt-2">
          <div className="absolute inset-0 px-2 pb-8 pt-2">
            <div className="relative h-full">
              {[25, 50, 75].map((line) => (
                <div
                  key={line}
                  className="absolute left-0 right-0 border-t border-white/10"
                  style={{ top: `${line}%` }}
                />
              ))}
              <div className="absolute bottom-0 left-0 right-0 flex h-full items-end gap-1">
                {points.map((point) => {
                  const height = `${Math.max((point.value / max) * 100, 1)}%`;
                  return (
                    <div key={`${point.label}-${point.value}`} className="flex min-w-0 flex-1 items-end justify-center">
                      <div
                        className={`w-full rounded-t-sm bg-gradient-to-t ${barClassName}`}
                        style={{ height }}
                        title={`${point.label}: ${valueFormatter ? valueFormatter(point.value) : point.value}`}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="absolute bottom-2 left-2 right-2">
            <div className="relative h-5">
              {xTicks.map((tick) => {
                const index = points.findIndex((p) => p.label === tick.label && p.value === tick.value);
                const x = points.length > 1 ? (index / (points.length - 1)) * 100 : 50;
                return (
                  <span
                    key={`${tick.label}-${index}`}
                    className="absolute top-0 w-20 -translate-x-1/2 truncate text-center text-[11px] text-fg-muted"
                    style={{ left: `${x}%` }}
                    title={tick.label}
                  >
                    {tick.label}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      </div>
      {xAxisTitle ? <p className="text-center text-[11px] uppercase tracking-[0.08em] text-fg-muted">{xAxisTitle}</p> : null}
    </div>
  );
}
