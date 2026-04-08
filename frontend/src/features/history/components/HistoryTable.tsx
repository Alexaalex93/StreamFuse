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

function shortPath(path: string | null): string {
  if (!path) {
    return "n/a";
  }
  const normalized = path.replace(/\\/g, "/");
  return normalized.length > 52 ? `...${normalized.slice(-52)}` : normalized;
}

export function HistoryTable({ sessions, expandedId, onToggleExpand }: HistoryTableProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-card shadow-premium">
      <table className="w-full text-sm">
        <thead className="bg-white/[0.03] text-left text-fg-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Session</th>
            <th className="px-4 py-3 font-medium">User</th>
            <th className="px-4 py-3 font-medium">Source</th>
            <th className="px-4 py-3 font-medium">Media</th>
            <th className="px-4 py-3 font-medium">Ended</th>
            <th className="px-4 py-3 font-medium">Bandwidth</th>
            <th className="px-4 py-3 font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => {
            const expanded = session.id === expandedId;
            return (
              <Fragment key={session.id}>
                <tr className="border-t border-white/10 align-top">
                  <td className="px-4 py-3">
                    <div className="max-w-[240px]">
                      <p className="truncate font-medium text-white">{session.title || session.file_name || "Untitled"}</p>
                      <p className="mt-1 truncate text-xs text-fg-muted">{shortPath(session.file_path)}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-fg">{session.user_name}</td>
                  <td className="px-4 py-3"><SourceBadge source={session.source} /></td>
                  <td className="px-4 py-3 text-fg-muted">{session.media_type}</td>
                  <td className="px-4 py-3 text-fg-muted">{fmt(session.ended_at || session.updated_at)}</td>
                  <td className="px-4 py-3"><BandwidthBadge bandwidthBps={session.bandwidth_bps} text={session.bandwidth_human} /></td>
                  <td className="px-4 py-3">
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
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-[220px_1fr]">
                        <PosterCard sessionId={session.id} title={session.title || "history poster"} />
                        <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-xs text-fg-muted">
                          <div className="grid grid-cols-2 gap-2">
                            <p><span className="text-white">Started:</span> {fmt(session.started_at)}</p>
                            <p><span className="text-white">Updated:</span> {fmt(session.updated_at)}</p>
                            <p><span className="text-white">IP:</span> {session.ip_address || "n/a"}</p>
                            <p><span className="text-white">Status:</span> {session.status}</p>
                            <p><span className="text-white">Resolution:</span> {session.resolution || "n/a"}</p>
                            <p><span className="text-white">Transcode:</span> {session.transcode_decision || "n/a"}</p>
                            <p><span className="text-white">Video:</span> {session.video_codec || "n/a"}</p>
                            <p><span className="text-white">Audio:</span> {session.audio_codec || "n/a"}</p>
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
