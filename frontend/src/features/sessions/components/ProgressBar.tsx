type ProgressBarProps = {
  value: number | null;
};

export function ProgressBar({ value }: ProgressBarProps) {
  if (value == null) {
    return <p className="text-xs text-fg-muted">Progress not available</p>;
  }

  const normalized = Math.max(0, Math.min(100, value));

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-fg-muted">Progress</span>
        <span className="text-white">{normalized.toFixed(0)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-emerald-400"
          style={{ width: `${normalized}%` }}
        />
      </div>
    </div>
  );
}
