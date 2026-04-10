import { Fragment } from "react";

import { UnifiedSession } from "@/types/session";

import { SourceBadge } from "@/shared/ui/badges/SourceBadge";

import { BandwidthBadge } from "@/features/sessions/components/BandwidthBadge";
import { PosterCard } from "@/features/sessions/components/PosterCard";

type HistoryTableProps = {
  sessions: UnifiedSession[];
  expandedId: number | null;
  onToggleExpand: (id: number) => void;
};

function fmt(value: string | null): string {
  if (!value) {
    return "n/a";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "n/a" : date.toLocaleString();
}

function mediaLabel(session: UnifiedSession): string {
  if (session.media_type === "episode") {
    return "series";
  }
  return session.media_type;
}

function episodeCode(session: UnifiedSession): string | null {
  const hasSeason = session.season_number != null;
  const hasEpisode = session.episode_number != null;
  if (!hasSeason && !hasEpisode) {
    return null;
  }

  const s = hasSeason ? `S${String(session.season_number).padStart(2, "0")}` : "";
  const e = hasEpisode ? `E${String(session.episode_number).padStart(2, "0")}` : "";
  return `${s}${e}` || null;
}

function rowTitle(session: UnifiedSession): string {
  if (session.media_type === "episode") {
    return session.series_title || session.title || session.file_name || "Untitled";
  }
  return session.title || session.file_name || "Untitled";
}

function rowSubtitle(session: UnifiedSession): string {
  if (session.media_type !== "episode") {
    return session.file_path || "n/a";
  }

  const series = (session.series_title || "").trim();
  const title = (session.title || "").replace(/\uFFFD/g, " ").trim();
  const code = episodeCode(session);

  if (/S\d{1,2}E\d{1,3}/i.test(title)) {
    return title;
  }

  const line = [series || null, code || null, title && title !== series ? title : null].filter(Boolean).join(" - ");
  return line || session.file_path || "n/a";
}

function toMbpsTextFromBps(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "n/a";
  }
  const mbps = value / 1_000_000;
  return `${mbps.toFixed(1)} Mbps`;
}

function extractBitrateText(session: UnifiedSession): string {
  const raw = session.raw_payload;
  if (raw && typeof raw === "object") {
    const map = raw as Record<string, unknown>;
    const mediaInfo = map.media_info as Record<string, unknown> | undefined;

    const bpsCandidates: Array<number | null> = [
      typeof mediaInfo?.video_bitrate_bps === "number" ? mediaInfo.video_bitrate_bps : null,
      typeof mediaInfo?.overall_bitrate_bps === "number" ? mediaInfo.overall_bitrate_bps : null,
      typeof map.video_bitrate === "number" ? map.video_bitrate : null,
      typeof map.stream_video_bitrate === "number" ? map.stream_video_bitrate : null,
      typeof map.bitrate === "number" ? map.bitrate : null,
      typeof map.stream_bitrate === "number" ? map.stream_bitrate : null,
    ];

    for (const candidate of bpsCandidates) {
      if (typeof candidate === "number" && candidate > 0) {
        if (candidate < 1_000_000) {
          return `${(candidate / 1000).toFixed(1)} Mbps`;
        }
        return toMbpsTextFromBps(candidate);
      }
    }

    const fileSize = typeof map.file_size === "number" ? map.file_size : null;
    const durationMs = typeof map.duration === "number" ? map.duration : session.duration_ms;
    if (fileSize && durationMs && durationMs > 0) {
      const approxBps = (fileSize * 8 * 1000) / durationMs;
      if (approxBps > 0) {
        return `~${toMbpsTextFromBps(approxBps)}`;
      }
    }
  }

  if (session.bandwidth_human && session.bandwidth_human !== "n/a") {
    return session.bandwidth_human;
  }

  if (typeof session.bandwidth_bps === "number" && session.bandwidth_bps > 0) {
    return toMbpsTextFromBps(session.bandwidth_bps);
  }

  return "n/a";
}

export function HistoryTable({ sessions, expandedId, onToggleExpand }: HistoryTableProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-card shadow-premium">
      <table className="w-full table-auto text-sm">
        <thead className="bg-white/[0.03] text-left text-fg-muted">
          <tr>
            <th className="px-3 py-3 font-medium">Session</th>
            <th className="px-3 py-3 font-medium whitespace-nowrap">User</th>
            <th className="px-3 py-3 font-medium whitespace-nowrap">Source</th>
            <th className="px-3 py-3 font-medium whitespace-nowrap">Media</th>
            <th className="px-3 py-3 font-medium whitespace-nowrap">Ended</th>
            <th className="px-3 py-3 font-medium whitespace-nowrap">Bandwidth</th>
            <th className="px-3 py-3 font-medium whitespace-nowrap">Action</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => {
            const expanded = session.id === expandedId;
            const bitrateText = extractBitrateText(session);

            return (
              <Fragment key={session.id}>
                <tr className="border-t border-white/10 align-top">
                  <td className="px-3 py-3">
                    <p className="break-words font-medium text-white">{rowTitle(session)}</p>
                    <p className="mt-1 break-all text-xs text-fg-muted">{rowSubtitle(session)}</p>
                  </td>
                  <td className="px-3 py-3 text-fg whitespace-nowrap">{session.user_name}</td>
                  <td className="px-3 py-3 whitespace-nowrap"><SourceBadge source={session.source} /></td>
                  <td className="px-3 py-3 text-fg-muted whitespace-nowrap">{mediaLabel(session)}</td>
                  <td className="px-3 py-3 text-fg-muted whitespace-nowrap">{fmt(session.ended_at || session.updated_at)}</td>
                  <td className="px-3 py-3 whitespace-nowrap"><BandwidthBadge bandwidthBps={session.bandwidth_bps} text={bitrateText} /></td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <button
                      type="button"
                      className="rounded-lg border border-white/15 px-3 py-1 text-xs text-fg-muted transition hover:bg-white/[0.06]"
                      onClick={() => onToggleExpand(session.id)}
                    >
                      {expanded ? "Hide" : "Details"}
                    </button>
                  </td>
                </tr>

                {expanded ? (
                  <tr className="border-t border-white/10 bg-white/[0.01]">
                    <td colSpan={7} className="px-4 py-4">
                      <div className="flex flex-col gap-4 md:flex-row">
                        <PosterCard
                          sessionId={session.id}
                          title={session.title || "history poster"}
                          variant="poster"
                          className="h-[280px] w-[186px] shrink-0"
                        />
                        <div className="min-h-[280px] flex-1 rounded-xl border border-white/10 bg-white/[0.02] p-4 text-xs text-fg-muted">
                          <div className="grid grid-cols-2 gap-2">
                            <p><span className="text-white">Started:</span> {fmt(session.started_at)}</p>
                            <p><span className="text-white">Updated:</span> {fmt(session.updated_at)}</p>
                            <p><span className="text-white">IP:</span> {session.ip_address || "n/a"}</p>
                            <p><span className="text-white">Status:</span> {session.status}</p>
                            <p><span className="text-white">Resolution:</span> {session.resolution || "n/a"}</p>
                            <p><span className="text-white">Transcode:</span> {session.transcode_decision || "n/a"}</p>
                            <p><span className="text-white">Video:</span> {session.video_codec || "n/a"}</p>
                            <p><span className="text-white">Audio:</span> {session.audio_codec || "n/a"}</p>
                            <p><span className="text-white">Bandwidth:</span> {bitrateText}</p>
                          </div>
                          <p className="mt-3 break-all rounded-lg bg-white/[0.03] px-2 py-2 text-fg">{session.file_path || "n/a"}</p>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

