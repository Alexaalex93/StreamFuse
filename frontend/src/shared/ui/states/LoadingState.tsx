export function LoadingState({ title = "Loading data..." }: { title?: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-card p-8 text-center">
      <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-primary/20 border-t-primary" />
      <p className="mt-4 font-medium text-white">{title}</p>
      <p className="text-sm text-fg-muted">StreamFuse is preparing your view.</p>
    </div>
  );
}
