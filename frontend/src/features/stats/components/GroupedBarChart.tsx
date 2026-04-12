type GroupedBarItem = {
  label: string;
  seriesA: number;
  seriesB: number;
};

type GroupedBarChartProps = {
  items: GroupedBarItem[];
  seriesALabel: string;
  seriesBLabel: string;
  valueFormatter?: (value: number) => string;
  yAxisTitle?: string;
  xAxisTitle?: string;
};

export function GroupedBarChart({
  items,
  seriesALabel,
  seriesBLabel,
  valueFormatter,
  yAxisTitle,
  xAxisTitle,
}: GroupedBarChartProps) {
  const max = Math.max(...items.flatMap((item) => [item.seriesA, item.seriesB]), 1);

  return (
    <div className="space-y-2">
      {yAxisTitle ? <p className="text-[11px] uppercase tracking-[0.08em] text-fg-muted">{yAxisTitle}</p> : null}
      <div className="space-y-3">
        {items.map((item) => {
          const a = (item.seriesA / max) * 100;
          const b = (item.seriesB / max) * 100;
          return (
            <div key={item.label} className="space-y-1">
              <div className="text-xs text-fg">{item.label}</div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="mb-1 flex items-center justify-between text-[11px] text-fg-muted">
                    <span>{seriesALabel}</span>
                    <span>{valueFormatter ? valueFormatter(item.seriesA) : item.seriesA}</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div className="h-full rounded-full bg-cyan-400" style={{ width: `${a}%` }} />
                  </div>
                </div>
                <div>
                  <div className="mb-1 flex items-center justify-between text-[11px] text-fg-muted">
                    <span>{seriesBLabel}</span>
                    <span>{valueFormatter ? valueFormatter(item.seriesB) : item.seriesB}</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div className="h-full rounded-full bg-amber-400" style={{ width: `${b}%` }} />
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {xAxisTitle ? <p className="text-center text-[11px] uppercase tracking-[0.08em] text-fg-muted">{xAxisTitle}</p> : null}
    </div>
  );
}
