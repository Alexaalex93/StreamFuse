import { getBackendBase } from "@/shared/api/client";
import { formatLocalTime } from "@/shared/lib/date";
import { SourceBadge } from "@/shared/ui/badges/SourceBadge";
import { Button } from "@/shared/ui/button";
import { UnifiedSession } from "@/types/session";

import { BandwidthBadge } from "./BandwidthBadge";
import { ProgressBar } from "./ProgressBar";

const FALLBACK_POSTER =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='450'><rect width='100%25' height='100%25' fill='%230b1324'/><text x='50%25' y='50%25' fill='%2394a3b8' font-size='18' text-anchor='middle' dominant-baseline='middle'>No poster</text></svg>";

function summarizePath(path: string | null): string | null {
  if (!path) {
    return null;
  }
  const normalized = path.replace(/\\/g, "/");
  if (normalized.length <= 54) {
    return normalized;
  }
  return `...${normalized.slice(-54)}`;
}

function getMediaInfoBitrate(session: UnifiedSession): number | null {
  const raw = session.raw_payload;
  if (!raw || typeof raw !== "object") {
    return null;
  }

  const mediaInfo = (raw as Record<string, unknown>).media_info;
  if (!mediaInfo || typeof mediaInfo !== "object") {
    return null;
  }

  const map = mediaInfo as Record<string, unknown>;
  const video = map.video_bitrate_bps;
  const overall = map.overall_bitrate_bps;

  if (typeof video === "number") {
    return video;
  }
  if (typeof overall === "number") {
    return overall;
  }
  return null;
}

export function SessionCard({
  session,
  onOpen,
}: {
  session: UnifiedSession;
  onOpen: (session: UnifiedSession) => void;
}) {
  const backend = getBackendBase();
  const posterSrc = `${backend}/api/v1/posters/${session.id}?width=320&height=480`;
  const backdropSrc = `${backend}/api/v1/posters/${session.id}?width=1280&height=720`;
  const pathSummary = summarizePath(session.file_path);
  const bitrateBps = getMediaInfoBitrate(session);

  return (
    <article className="relative overflow-hidden rounded-2xl border border-cyan-300/20 bg-card shadow-premium">
      <div
        className="absolute inset-0 bg-cover bg-center opacity-45"
        style={{ backgroundImage: `url(${backdropSrc})` }}
        aria-hidden
      />
      <div className="absolute inset-0 bg-slate-950/35 backdrop-blur-lg" aria-hidden />
      <div className="absolute inset-0 bg-gradient-to-r from-slate-950/95 via-slate-900/72 to-slate-900/78" aria-hidden />

      <div className="relative flex gap-4 p-4">
        <div className="shrink-0">
          <img
            src={posterSrc}
            alt={session.title || "Poster"}
            loading="lazy"
            className="h-32 w-[88px] rounded-lg border border-white/25 object-cover shadow-xl"
            onError={(event) => {
              event.currentTarget.src = FALLBACK_POSTER;
            }}
          />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate font-display text-[1.35rem] leading-tight text-white">
                {session.title || session.file_name || "Untitled session"}
              </h3>
              <p className="mt-1 text-base text-fg-muted">{session.user_name}</p>
            </div>
            <SourceBadge source={session.source} />
          </div>

          <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[0.95rem] text-fg-muted">
            <p>
              <span className="text-white">Type:</span> {session.media_type}
            </p>
            <p>
              <span className="text-white">IP:</span> {session.ip_address || "n/a"}
            </p>
            <p>
              <span className="text-white">Start:</span> {formatLocalTime(session.started_at)}
            </p>
            <p>
              <span className="text-white">Resolution:</span> {session.resolution || "n/a"}
            </p>
            <p>
              <span className="text-white">Transcode:</span> {session.transcode_decision || "n/a"}
            </p>
            <p>
              <span className="text-white">Player:</span> {session.player_name || session.client_name || "n/a"}
            </p>
          </div>

          <p
            className="mt-2 min-h-6 truncate rounded-md bg-white/[0.1] px-2 py-1 text-xs text-fg-muted"
            aria-hidden={pathSummary ? undefined : true}
          >
            {pathSummary || "\u00A0"}
          </p>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <BandwidthBadge bandwidthBps={session.bandwidth_bps} text={session.bandwidth_human} />
            {bitrateBps ? (
              <span className="rounded-full border border-white/25 bg-black/20 px-2.5 py-1 text-xs text-fg-muted">
                Bitrate: {Math.round(bitrateBps / 1_000_000)} Mbps
              </span>
            ) : null}
          </div>

          <div className="mt-2">
            <ProgressBar value={session.progress_percent} />
          </div>

          <div className="mt-3 flex justify-end">
            <Button variant="outline" onClick={() => onOpen(session)}>
              View Details
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}
