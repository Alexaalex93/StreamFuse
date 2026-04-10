import { getBackendBase } from "@/shared/api/client";
import { cn } from "@/shared/lib/cn";

const FALLBACK_POSTER =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='360' height='540'><rect width='100%25' height='100%25' fill='%23111b2f'/><text x='50%25' y='50%25' fill='%2394a3b8' font-size='16' text-anchor='middle' dominant-baseline='middle'>No poster</text></svg>";

type PosterCardProps = {
  sessionId: number;
  title: string;
  variant?: "poster" | "fanart";
  className?: string;
  imageClassName?: string;
};

export function PosterCard({
  sessionId,
  title,
  variant = "fanart",
  className,
  imageClassName,
}: PosterCardProps) {
  const query =
    variant === "poster"
      ? "?variant=poster&width=1000&height=1500"
      : "?variant=fanart&width=1920&height=1080";
  const src = `${getBackendBase()}/api/v1/posters/${sessionId}${query}`;

  return (
    <div className={cn("relative overflow-hidden rounded-xl border border-white/10 bg-black/30", className)}>
      <img
        src={src}
        alt={title}
        loading="lazy"
        className={cn(
          variant === "poster" ? "h-full w-full object-cover" : "h-36 w-full object-cover",
          imageClassName,
        )}
        onError={(event) => {
          event.currentTarget.src = FALLBACK_POSTER;
        }}
      />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
    </div>
  );
}
