import { Button } from "@/shared/ui/button";

export function SessionsPanel() {
  return (
    <section className="rounded-xl bg-panel p-5 shadow-sm ring-1 ring-slate-800">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-white">Active Sessions</h2>
        <Button type="button" variant="outline">
          Refresh
        </Button>
      </div>
      <p className="mt-2 text-sm text-slate-300">Scaffold ready: connect `/api/v1/sessions`.</p>
    </section>
  );
}
