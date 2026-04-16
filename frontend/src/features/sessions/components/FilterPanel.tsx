import { ChangeEvent, useEffect, useState } from "react";

import { MediaType, StreamSource } from "@/types/domain";

import { Button } from "@/shared/ui/button";
import { getStoredLanguage, UiLanguage } from "@/shared/lib/i18n";

const TEXT = {
  es: {
    user: "Usuario",
    userPlaceholder: "Buscar usuario",
    source: "Fuente",
    allSources: "Todas las fuentes",
    mediaType: "Tipo de medio",
    allMedia: "Todos los medios",
    movie: "Pelicula",
    episode: "Episodio",
    live: "Directo",
    fileTransfer: "Transferencia",
    other: "Otro",
    clearFilters: "Limpiar filtros",
  },
  en: {
    user: "User",
    userPlaceholder: "Search user",
    source: "Source",
    allSources: "All sources",
    mediaType: "Media Type",
    allMedia: "All media",
    movie: "Movie",
    episode: "Episode",
    live: "Live",
    fileTransfer: "File transfer",
    other: "Other",
    clearFilters: "Clear Filters",
  },
} as const;

type FilterPanelProps = {
  userQuery: string;
  source: "all" | StreamSource;
  mediaType: "all" | MediaType;
  onUserQueryChange: (value: string) => void;
  onSourceChange: (value: "all" | StreamSource) => void;
  onMediaTypeChange: (value: "all" | MediaType) => void;
  onClear: () => void;
};

export function FilterPanel({
  userQuery,
  source,
  mediaType,
  onUserQueryChange,
  onSourceChange,
  onMediaTypeChange,
  onClear,
}: FilterPanelProps) {
  const [lang, setLang] = useState<UiLanguage>(getStoredLanguage());
  useEffect(() => {
    const handler = (e: Event) => setLang((e as CustomEvent<{ language: UiLanguage }>).detail.language);
    window.addEventListener("streamfuse:language-changed", handler);
    return () => window.removeEventListener("streamfuse:language-changed", handler);
  }, []);

  const tx = TEXT[lang];

  return (
    <section className="rounded-2xl border border-white/10 bg-card p-4 shadow-premium">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          {tx.user}
          <input
            value={userQuery}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onUserQueryChange(event.target.value)}
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

        <div className="flex items-end justify-end">
          <Button variant="ghost" onClick={onClear}>
            {tx.clearFilters}
          </Button>
        </div>
      </div>
    </section>
  );
}
