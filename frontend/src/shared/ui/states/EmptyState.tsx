import { Button } from "@/shared/ui/button";

export function EmptyState({
  title = "No data yet",
  description = "When sessions arrive, this panel will populate automatically.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-white/20 bg-card/70 p-8 text-center">
      <p className="font-display text-2xl text-white">{title}</p>
      <p className="mt-2 text-sm text-fg-muted">{description}</p>
      <div className="mt-5 flex justify-center">
        <Button variant="outline">Reload</Button>
      </div>
    </div>
  );
}
