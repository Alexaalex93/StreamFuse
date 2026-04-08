import { ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type StatCardProps = {
  label: string;
  value: string;
  hint?: string;
  trend?: string;
  icon?: ReactNode;
};

export function StatCard({ label, value, hint, trend, icon }: StatCardProps) {
  return (
    <article className="rounded-2xl border border-white/10 bg-card p-5 shadow-premium">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fg-muted">{label}</p>
          <p className="mt-2 font-display text-3xl font-semibold text-white">{value}</p>
        </div>
        {icon ? <div className="rounded-lg border border-white/10 bg-white/[0.03] p-2">{icon}</div> : null}
      </div>
      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-fg-muted">{hint}</span>
        {trend ? <span className="font-medium text-accent">{trend}</span> : null}
      </div>
    </article>
  );
}
