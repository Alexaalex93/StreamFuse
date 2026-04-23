import { TopMediaItem } from "@/types/stats";

type TopMediaListProps = {
  items: TopMediaItem[];
  usersLabel?: string;
  userLabelSingular?: string;
};

export function TopMediaList({ items, usersLabel = "users", userLabelSingular = "user" }: TopMediaListProps) {
  return (
    <div className="space-y-3">
      {items.map((item, index) => {
        const posterSrc = item.sample_session_id ? `/api/v1/posters/${item.sample_session_id}?variant=poster` : "";
        return (
          <article key={`${item.title}-${index}`} className="flex items-center gap-3 rounded-xl border border-white/10 bg-panel/30 p-2">
            <div className="w-6 flex-none text-center text-sm font-semibold text-fg-muted">{index + 1}</div>
            <div className="h-14 w-10 flex-none overflow-hidden rounded-md border border-white/10 bg-black/30">
              {posterSrc ? (
                <img
                  src={posterSrc}
                  alt={item.title}
                  className="h-full w-full object-cover"
                  loading="lazy"
                  onError={(event) => {
                    event.currentTarget.style.display = "none";
                  }}
                />
              ) : null}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-fg" title={item.title}>{item.title}</p>
              <p className="text-xs text-fg-muted">{item.unique_users} {item.unique_users === 1 ? userLabelSingular : usersLabel}</p>
            </div>
          </article>
        );
      })}
    </div>
  );
}
