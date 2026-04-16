import { useEffect, useMemo, useState } from "react";

import { UnifiedSession } from "@/types/session";

import { getBackendBase } from "@/shared/api/client";
import { formatLocalDateTime } from "@/shared/lib/date";
import { getStoredLanguage, UiLanguage } from "@/shared/lib/i18n";
import { SourceBadge } from "@/shared/ui/badges/SourceBadge";
import { Button } from "@/shared/ui/button";

import { BandwidthBadge } from "./BandwidthBadge";
import { ProgressBar } from "./ProgressBar";

const TEXT = {
  es: {
    sessionDetails: "Detalles de sesion",
    close: "Cerrar",
    untitled: "Sesion sin titulo",
    untitledShort: "Sin titulo",
    techSnapshot: "Datos tecnicos",
    type: "Tipo",
    ip: "IP",
    resolution: "Resolucion",
    videoCodec: "Codec de video",
    audioCodec: "Codec de audio",
    transcode: "Transcodificacion",
    bitrate: "Bitrate",
    client: "Cliente",
    player: "Reproductor",
    timeline: "Linea de tiempo",
    started: "Inicio",
    ended: "Fin",
    updated: "Actualizado",
    path: "Ruta",
    relatedSessions: "Sesiones relacionadas",
    debugPayload: "Payload de depuracion",
    debugEnable: "Activar modo depuracion para ver el payload del proveedor.",
    hide: "Ocultar",
    show: "Mostrar",
    series: "SERIES",
  },
  en: {
    sessionDetails: "Session Details",
    close: "Close",
    untitled: "Untitled session",
    untitledShort: "Untitled",
    techSnapshot: "Technical Snapshot",
    type: "Type",
    ip: "IP",
    resolution: "Resolution",
    videoCodec: "Video codec",
    audioCodec: "Audio codec",
    transcode: "Transcode",
    bitrate: "Bitrate",
    client: "Client",
    player: "Player",
    timeline: "Timeline",
    started: "Started",
    ended: "Ended",
    updated: "Updated",
    path: "Path",
    relatedSessions: "Related Sessions",
    debugPayload: "Debug Payload",
    debugEnable: "Enable debug mode to inspect original provider payload.",
    hide: "Hide",
    show: "Show",
    series: "SERIES",
  },
} as const;

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

type MediaDetailsDrawerProps = {
  open: boolean;
  session: UnifiedSession | null;
  relatedSessions: UnifiedSession[];
  onClose: () => void;
};

export function MediaDetailsDrawer({ open, session, relatedSessions, onClose }: MediaDetailsDrawerProps) {
  const [lang, setLang] = useState<UiLanguage>(getStoredLanguage());
  useEffect(() => {
    const handler = (e: Event) => setLang((e as CustomEvent<{ language: UiLanguage }>).detail.language);
    window.addEventListener("streamfuse:language-changed", handler);
    return () => window.removeEventListener("streamfuse:language-changed", handler);
  }, []);
  const tx = TEXT[lang];

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

  function detailsMediaType(s: UnifiedSession): string {
    if (s.media_type === "episode") {
      return tx.series;
    }
    return upperValue(s.media_type);
  }

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
              <h3 className="font-display text-xl text-white">{tx.sessionDetails}</h3>
              <Button variant="ghost" onClick={onClose}>
                {tx.close}
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
                    {session.title || session.file_name || tx.untitled}
                  </h4>
                  <p className="mt-1 text-sm text-fg-muted">{session.user_name}</p>
                </div>
                <SourceBadge source={session.source} />
              </div>

              <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.techSnapshot}</p>
                <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs text-fg-muted">
                  <p><span className="text-white">{tx.type}:</span> {detailsMediaType(session)}</p>
                  <p><span className="text-white">{tx.ip}:</span> {upperValue(session.ip_address)}</p>
                  <p><span className="text-white">{tx.resolution}:</span> {upperValue(session.resolution)}</p>
                  <p><span className="text-white">{tx.videoCodec}:</span> {upperValue(session.video_codec)}</p>
                  <p><span className="text-white">{tx.audioCodec}:</span> {upperValue(session.audio_codec)}</p>
                  <p><span className="text-white">{tx.transcode}:</span> {upperValue(session.transcode_decision)}</p>
                  <p><span className="text-white">{tx.bitrate}:</span> {formatSessionBitrate(session)}</p>
                  <p><span className="text-white">{tx.client}:</span> {upperValue(session.client_name, false)}</p>
                  <p><span className="text-white">{tx.player}:</span> {upperValue(session.player_name, false)}</p>
                </div>

                <div className="mt-3">
                  <BandwidthBadge bandwidthBps={session.bandwidth_bps} text={session.bandwidth_human} />
                </div>

                <div className="mt-3">
                  <ProgressBar value={session.progress_percent} />
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4 text-xs text-fg-muted">
                <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.timeline}</p>
                <div className="mt-3 space-y-1">
                  <p><span className="text-white">{tx.started}:</span> {formatLocalDateTime(session.started_at)}</p>
                  <p><span className="text-white">{tx.ended}:</span> {formatLocalDateTime(session.ended_at)}</p>
                  <p><span className="text-white">{tx.updated}:</span> {formatLocalDateTime(session.updated_at)}</p>
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4 text-xs text-fg-muted">
                <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.path}</p>
                <p className="mt-2 break-all rounded-lg bg-white/[0.03] px-2 py-2 text-fg">{session.file_path || "n/a"}</p>
              </div>

              {relatedSessions.length > 0 ? (
                <div className="mt-4 rounded-xl border border-white/10 bg-card/70 p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.relatedSessions}</p>
                  <div className="mt-2 space-y-2">
                    {relatedSessions.slice(0, 4).map((item) => (
                      <div key={`${item.source}-${item.source_session_id}`} className="flex items-center justify-between rounded-lg bg-white/[0.03] px-3 py-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm text-white">{item.title || item.file_name || tx.untitledShort}</p>
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
                  <p className="text-xs uppercase tracking-[0.12em] text-fg-muted">{tx.debugPayload}</p>
                  <Button variant="ghost" onClick={() => setShowDebug((value) => !value)}>
                    {showDebug ? tx.hide : tx.show}
                  </Button>
                </div>

                {showDebug ? (
                  <pre className="max-h-64 overflow-auto rounded-lg bg-[#070d1a] p-3 text-[11px] text-fg-muted">
                    {JSON.stringify(session.raw_payload, null, 2)}
                  </pre>
                ) : (
                  <p className="text-xs text-fg-muted">{tx.debugEnable}</p>
                )}
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
