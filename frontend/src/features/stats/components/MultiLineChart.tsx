import { useMemo, useState } from "react";

type MultiLinePoint = {
  label: string;
  value: number;
};

type MultiLineSeries = {
  label: string;
  color: string;
  points: MultiLinePoint[];
};

type MultiLineChartProps = {
  series: MultiLineSeries[];
  valueFormatter?: (value: number) => string;
  yAxisTitle?: string;
  xAxisTitle?: string;
};

type NormalizedPoint = MultiLinePoint & { x: number; y: number };

type NormalizedSeries = {
  label: string;
  color: string;
  points: NormalizedPoint[];
};

function uniqueOrderedLabels(series: MultiLineSeries[]): string[] {
  const labels: string[] = [];
  const seen = new Set<string>();
  for (const s of series) {
    for (const p of s.points) {
      if (!seen.has(p.label)) {
        seen.add(p.label);
        labels.push(p.label);
      }
    }
  }
  return labels;
}

export function MultiLineChart({
  series,
  valueFormatter,
  yAxisTitle,
  xAxisTitle,
}: MultiLineChartProps) {
  const [hover, setHover] = useState<{ series: string; point: MultiLinePoint } | null>(null);

  const labels = useMemo(() => uniqueOrderedLabels(series), [series]);

  const normalized = useMemo(() => {
    if (series.length === 0 || labels.length === 0) {
      return { series: [] as NormalizedSeries[], min: 0, max: 1, labels: [] as string[] };
    }

    const maps = series.map((s) => {
      const m = new Map<string, number>();
      s.points.forEach((p) => m.set(p.label, p.value));
      return { label: s.label, color: s.color, map: m };
    });

    const allValues: number[] = [];
    maps.forEach((m) => {
      labels.forEach((label) => allValues.push(m.map.get(label) ?? 0));
    });

    const max = Math.max(...allValues, 1);
    const min = Math.min(...allValues, 0);
    const range = Math.max(max - min, 1);

    const out: NormalizedSeries[] = maps.map((m) => {
      const points: NormalizedPoint[] = labels.map((label, index) => {
        const value = m.map.get(label) ?? 0;
        const x = labels.length === 1 ? 50 : (index / (labels.length - 1)) * 100;
        const y = 100 - ((value - min) / range) * 100;
        return { label, value, x, y };
      });
      return { label: m.label, color: m.color, points };
    });

    return { series: out, min, max, labels };
  }, [series, labels]);

  const yTicks = useMemo(() => {
    const vals = [normalized.max, normalized.min + (normalized.max - normalized.min) * 0.66, normalized.min + (normalized.max - normalized.min) * 0.33, normalized.min];
    return vals.map((v) => (valueFormatter ? valueFormatter(v) : String(Math.round(v))));
  }, [normalized.max, normalized.min, valueFormatter]);

  const xTickIndexes = useMemo(() => {
    if (normalized.labels.length <= 1) return [0];
    const max = normalized.labels.length - 1;
    if (normalized.labels.length <= 6) return normalized.labels.map((_, idx) => idx);
    return [0, Math.floor(max * 0.25), Math.floor(max * 0.5), Math.floor(max * 0.75), max];
  }, [normalized.labels]);

  return (
    <div className="relative">
      {yAxisTitle ? <p className="mb-1 text-[11px] uppercase tracking-[0.08em] text-fg-muted">{yAxisTitle}</p> : null}

      <div className="mb-3 flex flex-wrap gap-3 text-xs text-fg-muted">
        {normalized.series.map((s) => (
          <div key={s.label} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />
            <span>{s.label}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-[68px_1fr] gap-2">
        <div className="flex h-52 flex-col justify-between text-[11px] text-fg-muted">
          {yTicks.map((tick, index) => (
            <span key={`${tick}-${index}`} className="truncate">{tick}</span>
          ))}
        </div>

        <svg viewBox="0 0 100 100" className="h-52 w-full overflow-visible" preserveAspectRatio="none">
          <g className="stroke-white/15" strokeWidth="0.4">
            <line x1="0" y1="20" x2="100" y2="20" />
            <line x1="0" y1="40" x2="100" y2="40" />
            <line x1="0" y1="60" x2="100" y2="60" />
            <line x1="0" y1="80" x2="100" y2="80" />
          </g>

          {normalized.series.map((s) => {
            const d = s.points.map((p, idx) => `${idx === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
            return <path key={s.label} d={d} fill="none" stroke={s.color} strokeWidth="0.42" />;
          })}

          {normalized.series.map((s) =>
            s.points.map((p, idx) => (
              <circle
                key={`${s.label}-${idx}`}
                cx={p.x}
                cy={p.y}
                r={0.32}
                fill={s.color}
                onMouseEnter={() => setHover({ series: s.label, point: { label: p.label, value: p.value } })}
                onMouseLeave={() => setHover(null)}
              />
            )),
          )}
        </svg>
      </div>

      <div className="mt-2 grid grid-cols-[68px_1fr] gap-2">
        <span />
        <div className="relative h-5">
          {xTickIndexes.map((idx) => {
            const label = normalized.labels[idx] ?? "";
            const x = normalized.labels.length <= 1 ? 50 : (idx / (normalized.labels.length - 1)) * 100;
            return (
              <span key={`${label}-${idx}`} className="absolute top-0 w-20 -translate-x-1/2 truncate text-center text-[11px] text-fg-muted" style={{ left: `${x}%` }} title={label}>
                {label}
              </span>
            );
          })}
        </div>
      </div>

      {xAxisTitle ? <p className="mt-2 text-center text-[11px] uppercase tracking-[0.08em] text-fg-muted">{xAxisTitle}</p> : null}

      {hover ? (
        <div className="pointer-events-none absolute right-2 top-2 max-w-[260px] rounded-lg border border-white/15 bg-[#050b16] px-2 py-1 text-xs text-fg">
          <p className="truncate">{hover.series}</p>
          <p className="truncate text-fg-muted">{hover.point.label}</p>
          <p className="text-cyan-200">{valueFormatter ? valueFormatter(hover.point.value) : hover.point.value}</p>
        </div>
      ) : null}
    </div>
  );
}

