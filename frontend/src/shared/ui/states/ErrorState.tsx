import { Button } from "@/shared/ui/button";

export function ErrorState({
  title = "Unable to load data",
  description = "Check backend connectivity and try again.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 p-8 text-center">
      <p className="font-display text-2xl text-rose-100">{title}</p>
      <p className="mt-2 text-sm text-rose-100/80">{description}</p>
      <div className="mt-5 flex justify-center">
        <Button variant="outline" className="border-rose-300/40 text-rose-50 hover:bg-rose-300/10">
          Retry
        </Button>
      </div>
    </div>
  );
}
