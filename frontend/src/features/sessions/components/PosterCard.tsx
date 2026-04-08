import { getBackendBase } from "@/shared/api/client";

const FALLBACK_POSTER =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='360' height='220'><rect width='100%25' height='100%25' fill='%23111b2f'/><text x='50%25' y='50%25' fill='%2394a3b8' font-size='16' text-anchor='middle' dominant-baseline='middle'>No poster</text></svg>";

type PosterCardProps = {
  sessionId: number;
  title: string;
};

export function PosterCard({ sessionId, title }: PosterCardProps) {
  const src = `${getBackendBase()}/api/v1/posters/${sessionId}`;

  return (
    <div className="relative overflow-hidden rounded-xl border border-white/10 bg-black/30">
      <img
        src={src}
        alt={title}
        loading="lazy"
        className="h-36 w-full object-cover"
        onError={(event) => {
          event.currentTarget.src = FALLBACK_POSTER;
        }}
      />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
    </div>
  );
}
