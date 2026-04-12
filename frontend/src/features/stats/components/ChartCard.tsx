import { ReactNode } from "react";

type ChartCardProps = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  rightSlot?: ReactNode;
  onClick?: () => void;
  selected?: boolean;
};

export function ChartCard({
  title,
  subtitle,
  children,
  rightSlot,
  onClick,
  selected = false,
}: ChartCardProps) {
  const isClickable = typeof onClick === "function";

  return (
    <section
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(event) => {
        if (!isClickable) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onClick?.();
        }
      }}
      className={[
        "rounded-2xl border bg-card p-5 shadow-premium",
        isClickable ? "cursor-pointer transition hover:border-cyan-300/40" : "",
        selected ? "border-cyan-300/70 ring-1 ring-cyan-300/30" : "border-white/10",
      ]
        .filter(Boolean)
        .join(" ")}
    >
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
