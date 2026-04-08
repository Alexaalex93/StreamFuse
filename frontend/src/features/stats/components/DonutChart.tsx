type DonutSlice = {
  label: string;
  value: number;
  color: string;
};

type DonutChartProps = {
  slices: DonutSlice[];
};

function arcPath(cx: number, cy: number, r: number, start: number, end: number): string {
  const startX = cx + r * Math.cos(start);
  const startY = cy + r * Math.sin(start);
  const endX = cx + r * Math.cos(end);
  const endY = cy + r * Math.sin(end);
  const large = end - start > Math.PI ? 1 : 0;

  return `M ${startX} ${startY} A ${r} ${r} 0 ${large} 1 ${endX} ${endY}`;
}

export function DonutChart({ slices }: DonutChartProps) {
  const total = Math.max(1, slices.reduce((sum, s) => sum + s.value, 0));
  let acc = -Math.PI / 2;

  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 120 120" className="h-36 w-36">
        <circle cx="60" cy="60" r="44" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="16" />
        {slices.map((slice) => {
          const span = (slice.value / total) * Math.PI * 2;
          const start = acc;
          const end = acc + span;
          acc = end;

          return (
            <path
              key={slice.label}
              d={arcPath(60, 60, 44, start, end)}
              fill="none"
              stroke={slice.color}
              strokeWidth="16"
              strokeLinecap="round"
            >
              <title>{`${slice.label}: ${slice.value}`}</title>
            </path>
          );
        })}
      </svg>

      <div className="space-y-2">
        {slices.map((slice) => (
          <div key={slice.label} className="flex items-center gap-2 text-xs text-fg-muted">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: slice.color }} />
            <span className="min-w-[80px]">{slice.label}</span>
            <span className="font-semibold text-fg">{slice.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
