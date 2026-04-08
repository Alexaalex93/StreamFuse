import { ReactNode } from "react";

type ChartCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  rightSlot?: ReactNode;
};

export function ChartCard({ title, subtitle, children, rightSlot }: ChartCardProps) {
  return (
    <section className="rounded-2xl border border-white/10 bg-card p-5 shadow-premium">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="font-display text-xl text-white">{title}</h3>
          {subtitle ? <p className="text-xs text-fg-muted">{subtitle}</p> : null}
        </div>
        {rightSlot}
      </div>
      {children}
    </section>
  );
}
