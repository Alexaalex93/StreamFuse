import { UnifiedSession } from "@/types/session";

import { SourceBadge } from "@/shared/ui/badges/SourceBadge";
import { Button } from "@/shared/ui/button";

import { BandwidthBadge } from "./BandwidthBadge";
import { PosterCard } from "./PosterCard";
import { ProgressBar } from "./ProgressBar";

function formatStart(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "unknown";
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function summarizePath(path: string | null): string | null {
  if (!path) {
    return null;
  }
  const normalized = path.replace(/\\/g, "/");
  if (normalized.length <= 44) {
    return normalized;
  }
  return `...${normalized.slice(-44)}`;
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
  const pathSummary = summarizePath(session.file_path);
  const bitrateBps = getMediaInfoBitrate(session);

  return (
    <article className="flex h-full flex-col rounded-2xl border border-white/10 bg-card p-4 shadow-premium">
      <PosterCard sessionId={session.id} title={session.title || "Untitled"} />

      <div className="mt-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="line-clamp-2 font-display text-lg leading-tight text-white">
            {session.title || session.file_name || "Untitled session"}
          </h3>
          <p className="mt-1 text-sm text-fg-muted">{session.user_name}</p>
        </div>
        <SourceBadge source={session.source} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs text-fg-muted">
        <p>
          <span className="text-white">Type:</span> {session.media_type}
        </p>
        <p>
          <span className="text-white">IP:</span> {session.ip_address || "n/a"}
        </p>
        <p>
          <span className="text-white">Start:</span> {formatStart(session.started_at)}
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
        className="mt-3 min-h-7 rounded-lg bg-white/[0.03] px-2 py-1 text-xs text-fg-muted"
        aria-hidden={pathSummary ? undefined : true}
      >
        {pathSummary || "\u00A0"}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <BandwidthBadge bandwidthBps={session.bandwidth_bps} text={session.bandwidth_human} />
        {bitrateBps ? (
          <span className="rounded-full border border-white/15 px-2.5 py-1 text-xs text-fg-muted">
            Bitrate: {Math.round(bitrateBps / 1_000_000)} Mbps
          </span>
        ) : null}
      </div>

      <div className="mt-3">
        <ProgressBar value={session.progress_percent} />
      </div>

      <div className="mt-4 flex justify-end">
        <Button variant="outline" onClick={() => onOpen(session)}>
          View Details
        </Button>
      </div>
    </article>
  );
}