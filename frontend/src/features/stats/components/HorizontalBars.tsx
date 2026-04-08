type BarItem = {
  label: string;
  value: number;
  hint?: string;
};

type HorizontalBarsProps = {
  items: BarItem[];
  valueFormatter?: (value: number) => string;
};

export function HorizontalBars({ items, valueFormatter }: HorizontalBarsProps) {
  const max = Math.max(...items.map((item) => item.value), 1);

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const width = (item.value / max) * 100;
        return (
          <div key={item.label} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="truncate text-fg">{item.label}</span>
              <span className="text-fg-muted">{valueFormatter ? valueFormatter(item.value) : item.value}</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400" style={{ width: `${width}%` }} />
            </div>
            {item.hint ? <p className="text-[11px] text-fg-muted">{item.hint}</p> : null}
          </div>
        );
      })}
    </div>
  );
}
