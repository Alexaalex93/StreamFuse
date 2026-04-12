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

function formatEpisodeCode(session: UnifiedSession): string | null {
  const hasSeason = session.season_number != null;
  const hasEpisode = session.episode_number != null;
  if (!hasSeason && !hasEpisode) {
    return null;
  }
  const s = hasSeason ? `S${String(session.season_number).padStart(2, "0")}` : "";
  const e = hasEpisode ? `E${String(session.episode_number).padStart(2, "0")}` : "";
  return `${s}${e}` || null;
}

function mediaTypeLabel(session: UnifiedSession): string {
  if (session.media_type === "episode") {
    return "series";
  }
  return session.media_type || "other";
}

function cardTitle(session: UnifiedSession): string {
  if (session.media_type === "episode") {
    return session.series_title || session.title || session.file_name || "Untitled";
  }
  return session.title || session.file_name || "Untitled";
}

function cardSubtitle(session: UnifiedSession): string | null {
  if (session.media_type !== "episode") {
    return null;
  }

  const series = (session.series_title || "").replace(/\uFFFD/g, " ").trim();
  const rawTitle = (session.title || "").replace(/\uFFFD/g, " ").trim();
  const code = formatEpisodeCode(session);

  let episodeTitle = rawTitle;
  if (series && episodeTitle.toLowerCase().startsWith(series.toLowerCase())) {
    episodeTitle = episodeTitle.slice(series.length).replace(/^\s*[-:|.]\s*/, "");
  }
  if (code && episodeTitle.toUpperCase().startsWith(code.toUpperCase())) {
    episodeTitle = episodeTitle.slice(code.length).replace(/^\s*[-:|.]\s*/, "");
  }
  if (series && episodeTitle.toLowerCase().startsWith(series.toLowerCase())) {
    episodeTitle = episodeTitle.slice(series.length).replace(/^\s*[-:|.]\s*/, "");
  }

  const parts = [series || null, code || null, episodeTitle || null].filter(Boolean);
  if (parts.length === 0) {
    return code;
  }

  return parts.join(" - ");
}

function extractBitrate(session: UnifiedSession): string {
  const raw = session.raw_payload;
  const map = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : undefined;
  const mediaInfo = map?.media_info as Record<string, unknown> | undefined;

  const bpsFromMedia =
    typeof mediaInfo?.overall_bitrate_bps === "number"
      ? mediaInfo.overall_bitrate_bps
      : typeof mediaInfo?.video_bitrate_bps === "number"
        ? mediaInfo.video_bitrate_bps
        : null;

  if (typeof bpsFromMedia === "number" && bpsFromMedia > 0) {
    return `${(bpsFromMedia / 1_000_000).toFixed(1)} Mbps`;
  }

  // For SFTPGo/Samba we only trust mediainfo XML bitrate.
  if (session.source === "sftpgo" || session.source === "samba") {
    return "n/a";
  }

  const kbps =
    typeof map?.stream_bitrate === "number"
      ? map.stream_bitrate
      : typeof map?.bitrate === "number"
        ? map.bitrate
        : null;

  if (typeof kbps === "number" && kbps > 0) {
    return `${Math.round(kbps / 1000)} Mbps`;
  }

  return session.bandwidth_human || "n/a";
}


export function SessionCard({ session, onOpen }: SessionCardProps) {
  const backend = getBackendBase();
  const posterSrc = `${backend}/api/v1/posters/${session.id}?variant=poster&width=1000&height=1500`;
  const fanartSrc = `${backend}/api/v1/posters/${session.id}?variant=fanart&width=1920&height=1080`;
  const progress = Math.max(0, Math.min(100, session.progress_percent ?? 0));
  const pathText = summarizePath(session.file_path);
  const bitrateText = extractBitrate(session);
  const subtitle = cardSubtitle(session);

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
      <div className="relative h-[180px]">
        <img
          src={fanartSrc}
          alt=""
          aria-hidden
          className="absolute inset-0 h-full w-full object-cover object-top opacity-65 blur-[2px]"
        />
        <div className="absolute inset-0 bg-slate-950/30" aria-hidden />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/92 via-slate-900/52 to-slate-900/68" aria-hidden />

        <div className="relative flex h-full gap-3 p-3">
          <div className="h-full aspect-[2/3] shrink-0 overflow-hidden rounded-lg border border-white/20 bg-black/35 shadow-lg">
            <img
              src={posterSrc}
              alt={session.title || "Poster"}
              className="h-full w-full object-cover"
              onError={(event) => {
                event.currentTarget.src = FALLBACK_POSTER;
              }}
            />
          </div>

          <div className="min-w-0 flex-1">
            <div className="mb-2 flex justify-end">
              <SourceBadge source={session.source} />
            </div>

            <div className="grid grid-cols-[76px_1fr] gap-x-2 gap-y-1 text-[0.8rem] leading-4 text-fg-muted">
              <span className="text-fg-muted/85">TYPE</span><span className="truncate">{mediaTypeLabel(session)}</span>
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

        <div className="mb-1 flex items-center justify-start gap-2">
          <BandwidthBadge bandwidthBps={session.bandwidth_bps} text={bitrateText} />
        </div>

        <div className="h-2 w-full overflow-hidden rounded-full bg-white/15">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-emerald-400"
            style={{ width: `${progress}%` }}
          />
        </div>

        <div className="mt-3 flex items-end justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[1rem] font-semibold text-white">{cardTitle(session)}</p>
            {subtitle ? <p className="truncate text-xs text-fg-muted">{subtitle}</p> : null}
          </div>
          <p className="shrink-0 text-sm text-fg-muted">{session.user_name}</p>
        </div>
      </div>
    </article>
  );
}
