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
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='450'><rect width='100%25' height='100%25' fill='%230b1324'/><text x='50%25' y='50%25' fill='%2394a3b8' font-size='18' text-anchor='middle' dominant-baseline='middle'>No poster</text></svg>";

function summarizePath(path: string | null): string {
  if (!path) {
    return "n/a";
  }
  const normalized = path.replace(/\\/g, "/");
  if (normalized.length <= 44) {
    return normalized;
  }
  return `...${normalized.slice(-44)}`;
}

function fmtDuration(ms: number | null): string {
  if (!ms || ms <= 0) {
    return "--:--";
  }
  const total = Math.floor(ms / 1000);
  const min = Math.floor(total / 60);
  const sec = total % 60;
  return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export function SessionCard({ session, onOpen }: SessionCardProps) {
  const backend = getBackendBase();
  const posterSrc = `${backend}/api/v1/posters/${session.id}?width=320&height=480`;
  const fanartSrc = `${backend}/api/v1/posters/${session.id}?width=1280&height=720`;
  const progress = Math.max(0, Math.min(100, session.progress_percent ?? 0));

  return (
    <article
      className="group overflow-hidden rounded-2xl border border-cyan-300/20 bg-[#0b1222] shadow-premium cursor-pointer"
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
      <div className="relative h-[220px]">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${fanartSrc})` }}
          aria-hidden
        />
        <div className="absolute inset-0 bg-slate-950/30 backdrop-blur-md" aria-hidden />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-slate-900/60 to-slate-900/70" aria-hidden />

        <div className="relative flex h-full gap-4 p-3">
          <img
            src={posterSrc}
            alt={session.title || "Poster"}
            className="h-full w-[92px] rounded-lg border border-white/25 object-cover shadow-lg"
            onError={(event) => {
              event.currentTarget.src = FALLBACK_POSTER;
            }}
          />

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-[1.05rem] font-semibold text-white">{session.title || session.file_name || "Untitled"}</p>
                <p className="text-sm text-fg-muted">{session.user_name}</p>
              </div>
              <SourceBadge source={session.source} />
            </div>

            <div className="mt-2 grid grid-cols-[78px_1fr] gap-x-2 gap-y-1 text-sm text-fg-muted">
              <span className="text-fg-muted/80">TYPE</span><span>{session.media_type}</span>
              <span className="text-fg-muted/80">START</span><span>{formatLocalTime(session.started_at)}</span>
              <span className="text-fg-muted/80">PLAYER</span><span className="truncate">{session.player_name || session.client_name || "n/a"}</span>
              <span className="text-fg-muted/80">QUALITY</span><span>{session.resolution || "n/a"}</span>
              <span className="text-fg-muted/80">STREAM</span><span>{session.transcode_decision || "n/a"}</span>
              <span className="text-fg-muted/80">IP</span><span className="truncate">{session.ip_address || "n/a"}</span>
              <span className="text-fg-muted/80">PATH</span><span className="truncate">{summarizePath(session.file_path)}</span>
            </div>

            <div className="mt-2 flex items-center justify-between gap-2">
              <BandwidthBadge bandwidthBps={session.bandwidth_bps} text={session.bandwidth_human} />
              <span className="text-xs text-fg-muted">{progress.toFixed(0)}%</span>
            </div>

            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/15">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-sky-400 to-emerald-400"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-white/10 bg-[#0f1628] px-3 py-2">
        <div className="mb-2 h-[3px] w-full rounded-full bg-gradient-to-r from-amber-400 via-orange-400 to-amber-500" />
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-[1rem] font-semibold text-white">{session.title || session.file_name || "Untitled"}</p>
            <p className="truncate text-sm text-fg-muted">
              {session.series_title ? `${session.series_title} · ` : ""}
              {session.season_number != null ? `S${String(session.season_number).padStart(2, "0")}` : ""}
              {session.episode_number != null ? `E${String(session.episode_number).padStart(2, "0")}` : ""}
            </p>
          </div>
          <div className="text-right text-xs text-fg-muted">
            <p>{session.user_name}</p>
            <p>{fmtDuration(session.duration_ms)}</p>
          </div>
        </div>
      </div>
    </article>
  );
}
