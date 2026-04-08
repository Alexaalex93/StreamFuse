import { getBackendBase } from "@/shared/api/client";
import { formatLocalTime } from "@/shared/lib/date";
import { SourceBadge } from "@/shared/ui/badges/SourceBadge";
import { UnifiedSession } from "@/types/session";

import { BandwidthBadge } from "./BandwidthBadge";

type SessionCardProps = {
  session: UnifiedSession;
  onOpen: (session: UnifiedSession) => void;
};

const FALLBACK_POSTER =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='2000' height='3000'><rect width='100%25' height='100%25' fill='%230b1324'/><text x='50%25' y='50%25' fill='%2394a3b8' font-size='90' text-anchor='middle' dominant-baseline='middle'>No poster</text></svg>";

function summarizePath(path: string | null): string {
  if (!path) {
    return "n/a";
  }
  const normalized = path.replace(/\\/g, "/");
  if (normalized.length <= 80) {
    return normalized;
  }
  return `...${normalized.slice(-80)}`;
}

function formatEpisode(session: UnifiedSession): string {
  const hasSeason = session.season_number != null;
  const hasEpisode = session.episode_number != null;
  if (!hasSeason && !hasEpisode) {
    return session.media_type;
  }
  const s = hasSeason ? `S${String(session.season_number).padStart(2, "0")}` : "";
  const e = hasEpisode ? `E${String(session.episode_number).padStart(2, "0")}` : "";
  return `${s}${e}`;
}

function extractBitrate(session: UnifiedSession): string {
  const raw = session.raw_payload;
  if (!raw || typeof raw !== "object") {
    return "n/a";
  }

  const map = raw as Record<string, unknown>;
  const mediaInfo = map.media_info as Record<string, unknown> | undefined;

  const bpsFromMedia =
    typeof mediaInfo?.video_bitrate_bps === "number"
      ? mediaInfo.video_bitrate_bps
      : typeof mediaInfo?.overall_bitrate_bps === "number"
        ? mediaInfo.overall_bitrate_bps
        : null;

  if (typeof bpsFromMedia === "number" && bpsFromMedia > 0) {
    return `${Math.round(bpsFromMedia / 1_000_000)} Mbps`;
  }

  const kbps =
    typeof map.stream_bitrate === "number"
      ? map.stream_bitrate
      : typeof map.bitrate === "number"
        ? map.bitrate
        : null;

  if (typeof kbps === "number" && kbps > 0) {
    return `${Math.round(kbps / 1000)} Mbps`;
  }

  return "n/a";
}

export function SessionCard({ session, onOpen }: SessionCardProps) {
  const backend = getBackendBase();
  const posterSrc = `${backend}/api/v1/posters/${session.id}?variant=poster&width=1000&height=1500`;
  const fanartSrc = `${backend}/api/v1/posters/${session.id}?variant=fanart&width=1920&height=1080`;
  const progress = Math.max(0, Math.min(100, session.progress_percent ?? 0));
  const pathText = summarizePath(session.file_path);
  const bitrateText = extractBitrate(session);

  return (
    <article
      className="group overflow-hidden rounded-2xl border border-cyan-300/25 bg-[#0b1222] shadow-premium"
      onClick={() => onOpen(session)}
      role="button"
      tabIndex={0}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen(session);
        }
      }}
    >
      <div className="relative h-[210px]">
        <div
          className="absolute inset-0 bg-no-repeat bg-contain bg-center opacity-55"
          style={{ backgroundImage: `url(${fanartSrc})` }}
          aria-hidden
        />
        <div className="absolute inset-0 bg-slate-950/25 backdrop-blur-[1.5px]" aria-hidden />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/88 via-slate-900/42 to-slate-900/62" aria-hidden />

        <div className="relative flex h-full gap-3 p-3">
          <div className="flex h-full w-[96px] shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/20 bg-black/35 shadow-lg">
            <img
              src={posterSrc}
              alt={session.title || "Poster"}
              className="h-full w-full object-contain"
              onError={(event) => {
                event.currentTarget.src = FALLBACK_POSTER;
              }}
            />
          </div>

          <div className="min-w-0 flex-1">
            <div className="mb-2 flex justify-end">
              <SourceBadge source={session.source} />
            </div>

            <div className="grid grid-cols-[86px_1fr] gap-x-2 gap-y-1 text-[0.95rem] leading-5 text-fg-muted">
              <span className="text-fg-muted/85">TYPE</span><span className="truncate">{formatEpisode(session)}</span>
              <span className="text-fg-muted/85">START</span><span>{formatLocalTime(session.started_at)}</span>
              <span className="text-fg-muted/85">PLAYER</span><span className="truncate">{session.player_name || session.client_name || "n/a"}</span>
              <span className="text-fg-muted/85">QUALITY</span><span>{session.resolution || "n/a"}</span>
              <span className="text-fg-muted/85">STREAM</span><span className="truncate">{session.transcode_decision || "n/a"}</span>
              <span className="text-fg-muted/85">IP</span><span className="truncate">{session.ip_address || "n/a"}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-[#0f1628] px-3 pb-3 pt-2">
        <p className="mb-2 truncate rounded-md bg-white/[0.08] px-2 py-1 text-xs text-fg-muted">{pathText}</p>

        <div className="mb-1 flex items-center justify-between gap-2">
          <BandwidthBadge bandwidthBps={session.bandwidth_bps} text={session.bandwidth_human} />
          <span className="text-xs text-fg-muted">Bitrate: {bitrateText}</span>
        </div>

        <div className="h-2 w-full overflow-hidden rounded-full bg-white/15">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-emerald-400"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="mt-3 flex items-end justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[1rem] font-semibold text-white">{session.title || session.file_name || "Untitled"}</p>
          </div>
          <p className="shrink-0 text-sm text-fg-muted">{session.user_name}</p>
        </div>
      </div>
    </article>
  );
}


