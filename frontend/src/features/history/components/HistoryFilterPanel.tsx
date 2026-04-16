import { ChangeEvent, useEffect, useState } from "react";

import { MediaType, StreamSource } from "@/types/domain";

import { Button } from "@/shared/ui/button";
import { getStoredLanguage, UiLanguage } from "@/shared/lib/i18n";

const TEXT = {
  es: {
    filters: "Filtros",
    searchText: "Texto de busqueda",
    searchPlaceholder: "titulo, ruta, ip",
    user: "Usuario",
    userPlaceholder: "alice",
    source: "Fuente",
    allSources: "Todas las fuentes",
    mediaType: "Tipo de medio",
    allMedia: "Todos los medios",
    movie: "Pelicula",
    episode: "Episodio",
    live: "Directo",
    fileTransfer: "Transferencia",
    other: "Otro",
    from: "Desde",
    to: "Hasta",
    clearFilters: "Limpiar filtros",
  },
  en: {
    filters: "Filters",
    searchText: "Search text",
    searchPlaceholder: "title, path, ip",
    user: "User",
    userPlaceholder: "alice",
    source: "Source",
    allSources: "All sources",
    mediaType: "Media Type",
    allMedia: "All media",
    movie: "Movie",
    episode: "Episode",
    live: "Live",
    fileTransfer: "File transfer",
    other: "Other",
    from: "From",
    to: "To",
    clearFilters: "Clear Filters",
  },
} as const;

type HistoryFilterPanelProps = {
  userName: string;
  source: "all" | StreamSource;
  mediaType: "all" | MediaType;
  dateFrom: string;
  dateTo: string;
  text: string;
  onUserNameChange: (value: string) => void;
  onSourceChange: (value: "all" | StreamSource) => void;
  onMediaTypeChange: (value: "all" | MediaType) => void;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onTextChange: (value: string) => void;
  onClear: () => void;
};

export function HistoryFilterPanel({
  userName,
  source,
  mediaType,
  dateFrom,
  dateTo,
  text,
  onUserNameChange,
  onSourceChange,
  onMediaTypeChange,
  onDateFromChange,
  onDateToChange,
  onTextChange,
  onClear,
}: HistoryFilterPanelProps) {
  const [lang, setLang] = useState<UiLanguage>(getStoredLanguage());
  useEffect(() => {
    const handler = (e: Event) => setLang((e as CustomEvent<{ language: UiLanguage }>).detail.language);
    window.addEventListener("streamfuse:language-changed", handler);
    return () => window.removeEventListener("streamfuse:language-changed", handler);
  }, []);

  const tx = TEXT[lang];

  return (
    <aside className="rounded-2xl border border-white/10 bg-card p-4 shadow-premium">
      <h3 className="font-display text-lg text-white">{tx.filters}</h3>

      <div className="mt-4 space-y-3">
        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          {tx.searchText}
          <input
            value={text}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onTextChange(event.target.value)}
            placeholder={tx.searchPlaceholder}
            className="rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          {tx.user}
          <input
            value={userName}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onUserNameChange(event.target.value)}
            placeholder={tx.userPlaceholder}
            className="rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          {tx.source}
          <select
            value={source}
            onChange={(event) => onSourceChange(event.target.value as "all" | StreamSource)}
            className="rounded-lg border border-white/15 bg-[#0b1528] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          >
            <option value="all">{tx.allSources}</option>
            <option value="tautulli">Tautulli</option>
            <option value="sftpgo">SFTPGo</option>
            <option value="samba">Samba</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          {tx.mediaType}
          <select
            value={mediaType}
            onChange={(event) => onMediaTypeChange(event.target.value as "all" | MediaType)}
            className="rounded-lg border border-white/15 bg-[#0b1528] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          >
            <option value="all">{tx.allMedia}</option>
            <option value="movie">{tx.movie}</option>
            <option value="episode">{tx.episode}</option>
            <option value="live">{tx.live}</option>
            <option value="file_transfer">{tx.fileTransfer}</option>
            <option value="other">{tx.other}</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          {tx.from}
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => onDateFromChange(event.target.value)}
            className="rounded-lg border border-white/15 bg-[#0b1528] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          {tx.to}
          <input
            type="date"
            value={dateTo}
            onChange={(event) => onDateToChange(event.target.value)}
            className="rounded-lg border border-white/15 bg-[#0b1528] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          />
        </label>

        <Button variant="ghost" className="w-full" onClick={onClear}>
          {tx.clearFilters}
        </Button>
      </div>
    </aside>
  );
}
