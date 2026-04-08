import { StreamSource } from "@/types/domain";

import { cn } from "@/shared/lib/cn";

type SourceBadgeProps = {
  source: StreamSource;
};

const sourceStyles: Record<StreamSource, string> = {
  tautulli: "border-cyan-300/40 bg-cyan-400/10 text-cyan-200",
  sftpgo: "border-emerald-300/40 bg-emerald-400/10 text-emerald-200",
};

export function SourceBadge({ source }: SourceBadgeProps) {
  return (
    <span className={cn("inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold uppercase", sourceStyles[source])}>
      {source}
    </span>
  );
}
