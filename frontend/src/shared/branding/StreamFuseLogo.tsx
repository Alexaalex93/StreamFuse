import { cn } from "@/shared/lib/cn";

type StreamFuseLogoProps = {
  className?: string;
};

export function StreamFuseLogo({ className }: StreamFuseLogoProps) {
  return (
    <svg
      viewBox="0 0 120 120"
      role="img"
      aria-label="StreamFuse"
      className={cn("drop-shadow-[0_0_24px_rgba(79,70,229,0.35)]", className)}
    >
      <defs>
        <linearGradient id="streamfuseGradient" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#34d399" />
        </linearGradient>
      </defs>
      <rect x="8" y="8" width="104" height="104" rx="26" fill="#0b1424" stroke="rgba(255,255,255,0.2)" />
      <path d="M28 74h62c4 0 7-3 7-7V45" fill="none" stroke="url(#streamfuseGradient)" strokeWidth="10" strokeLinecap="round" />
      <path d="M28 46h36" fill="none" stroke="#93c5fd" strokeWidth="10" strokeLinecap="round" />
      <circle cx="91" cy="42" r="9" fill="#34d399" />
    </svg>
  );
}
