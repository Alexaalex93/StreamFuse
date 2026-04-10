import { useEffect, useMemo, useState } from "react";

import { UnifiedSession } from "@/types/session";

import { getBackendBase } from "@/shared/api/client";
import { formatLocalDateTime } from "@/shared/lib/date";
import { SourceBadge } from "@/shared/ui/badges/SourceBadge";
import { Button } from "@/shared/ui/button";

import { BandwidthBadge } from "./BandwidthBadge";
import { ProgressBar } from "./ProgressBar";

const FALLBACK_POSTER =
  "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='450'><rect width='100%25' height='100%25' fill='%23111b2f'/><text x='50%25' y='50%25' fill='%2394a3b8' font-size='18' text-anchor='middle' dominant-baseline='middle'>No poster</text></svg>";

function formatBpsToHuman(bps: number): string {
  const mbps = bps / 1_000_000;
  if (mbps >= 1) {
    return `${Math.round(mbps)} Mbps`;
  }
  return `${Math.round(bps / 1000)} Kbps`;
}

function formatSessionBitrate(session: UnifiedSession): string {
  const raw = session.raw_payload;
  if (raw && typeof raw === "object") {
    const map = raw as Record<string, unknown>;
    const mediaInfo = map.media_info as Record<string, unknown> | undefined;

    const bpsFromMedia =
      typeof mediaInfo?.video_bitrate_bps === "number"
        ? mediaInfo.video_bitrate_bps
        : typeof mediaInfo?.overall_bitrate_bps === "number"
          ? mediaInfo.overall_bitrate_bps
          : null;

    if (typeof bpsFromMedia === "number" && bpsFromMedia > 0) {
      return formatBpsToHuman(bpsFromMedia);
    }

    const kbps =
      typeof map.stream_bitrate === "number"
        ? map.stream_bitrate
        : typeof map.bitrate === "number"
          ? map.bitrate
          : null;

    if (typeof kbps === "number" && kbps > 0) {
      return formatBpsToHuman(kbps * 1000);
    }
  }

  if (typeof session.bandwidth_bps === "number" && session.bandwidth_bps > 0) {
    return formatBpsToHuman(session.bandwidth_bps);
  }

  return "N/A";
}

function upperValue(value: string | number | null | undefined, uppercase = true): string {
  if (value == null || value === "") {
    return "N/A";
  }
  const text = String(value);
  return uppercase ? text.toUpperCase() : text;
}


function detailsMediaType(session: UnifiedSession): string {
  if (session.media_type === "episode") {
    return "SERIES";
  }
  return upperValue(session.media_type);
}
type MediaDetailsDrawerProps = {
  open: boolean;
  session: UnifiedSession | null;
  relatedSessions: UnifiedSession[];
  onClose: () => void;
};

export function MediaDetailsDrawer({ open, session, relatedSessions, onClose }: MediaDetailsDrawerProps) {
  const [showDebug, setShowDebug] = useState(false);

  useEffect(() => {
    setShowDebug(false);
  }, [session?.id]);

  const posterSrc = useMemo(() => {
    if (!session) {
      return FALLBACK_POSTER;
    }
    return `${getBackendBase()}/api/v1/posters/${session.id}?variant=poster&width=1000&height=1500`;
  }, [session]);

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-[#04060c]/70 backdrop-blur-sm transition ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={onClose}
      />

      <aside
        className={`fixed right-0 top-0 z-50 h-full w-full max-w-xl border-l border-white/10 bg-[#0b1324] p-5 shadow-[0_0_60px_rgba(0,0,0,0.55)] transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {!session ? null : (
          <div className="flex h-full flex-col">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-display text-xl text-white">Session Details</h3>
              <Button variant="ghost" onClick={onClose}>
                Close
              </Button>
            </div>

            <div className="overflow-y-auto pr-1">
              <div className="mx-auto w-fit overflow-hidden rounded-2xl border border-white/10 bg-[#060d1a] shadow-lg">
                <img
                  src={posterSrc}
                  alt={session.title || "session poster"}
                  className="h-72 w-48 object-cover"
                  onError={(event) => {
                    event.currentTarget.src = FALLBACK_POSTER;
                  }}
                />
              </div>

              <div className="mt-4 flex items-start justify-between gap-4">
                <div>
                  <h4 className="font-display text-2xl leading-tight text-white">
                    {session.title || session.file_name || "Untitled session"}
                  </h4>
                  <p className="mt-1 text-sm text-fg-muted">{session.user_name}</p>
                </div>
                <SourceBadge source={session.source} />
              </div>

              <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">Technical Snapshot</p>
                <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs text-fg-muted">
                  <p><span className="text-white">Type:</span> {detailsMediaType(session)}</p>
                  <p><span className="text-white">IP:</span> {upperValue(session.ip_address)}</p>
                  <p><span className="text-white">Resolution:</span> {upperValue(session.resolution)}</p>
                  <p><span className="text-white">Video codec:</span> {upperValue(session.video_codec)}</p>
                  <p><span className="text-white">Audio codec:</span> {upperValue(session.audio_codec)}</p>
                  <p><span className="text-white">Transcode:</span> {upperValue(session.transcode_decision)}</p>
                  <p><span className="text-white">Bitrate:</span> {formatSessionBitrate(session)}</p>
                  <p><span className="text-white">Client:</span> {upperValue(session.client_name, false)}</p>
                  <p><span className="text-white">Player:</span> {upperValue(session.player_name, false)}</p>
                </div>

                <div className="mt-3">
                  <BandwidthBadge bandwidthBps={session.bandwidth_bps} text={session.bandwidth_human} />
                </div>

                <div className="mt-3">
                  <ProgressBar value={session.progress_percent} />
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4 text-xs text-fg-muted">
                <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">Timeline</p>
                <div className="mt-3 space-y-1">
                  <p><span className="text-white">Started:</span> {formatLocalDateTime(session.started_at)}</p>
                  <p><span className="text-white">Ended:</span> {formatLocalDateTime(session.ended_at)}</p>
                  <p><span className="text-white">Updated:</span> {formatLocalDateTime(session.updated_at)}</p>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4 text-xs text-fg-muted">
                <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">Path</p>
                <p className="mt-2 break-all rounded-lg bg-white/[0.03] px-2 py-2 text-fg">{session.file_path || "n/a"}</p>
              </div>

              {relatedSessions.length > 0 ? (
                <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">Related Sessions</p>
                  <div className="mt-2 space-y-2">
                    {relatedSessions.slice(0, 4).map((item) => (
                      <div key={`${item.source}-${item.source_session_id}`} className="flex items-center justify-between rounded-lg bg-white/[0.03] px-3 py-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm text-white">{item.title || item.file_name || "Untitled"}</p>
                          <p className="text-xs text-fg-muted">{item.user_name}</p>
                        </div>
                        <SourceBadge source={item.source} />
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4">
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">Debug Payload</p>
                  <Button variant="ghost" onClick={() => setShowDebug((value) => !value)}>
                    {showDebug ? "Hide" : "Show"}
                  </Button>
                </div>

                {showDebug ? (
                  <pre className="max-h-64 overflow-auto rounded-lg bg-[#070d1a] p-3 text-[11px] text-fg-muted">
                    {JSON.stringify(session.raw_payload, null, 2)}
                  </pre>
                ) : (
                  <p className="text-xs text-fg-muted">Enable debug mode to inspect original provider payload.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}


