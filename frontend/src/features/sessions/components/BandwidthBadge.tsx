import { cn } from "@/shared/lib/cn";

type BandwidthBadgeProps = {
  bandwidthBps: number | null;
  text?: string | null;
};

function toHuman(bps: number): string {
  const mbps = bps / 1_000_000;
  if (mbps >= 1) {
    return `${mbps.toFixed(1)} Mbps`;
  }
  const kbps = bps / 1_000;
  return `${kbps.toFixed(1)} Kbps`;
}

export function BandwidthBadge({ bandwidthBps, text }: BandwidthBadgeProps) {
  const label = text || (bandwidthBps ? toHuman(bandwidthBps) : "n/a");
  const high = (bandwidthBps ?? 0) >= 15_000_000;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
        high
          ? "border-emerald-300/40 bg-emerald-400/10 text-emerald-200"
          : "border-cyan-300/40 bg-cyan-400/10 text-cyan-200",
      )}
    >
      {label}
    </span>
  );
}
