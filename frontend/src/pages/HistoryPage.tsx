import { useEffect, useMemo, useState } from "react";

import { MediaType, StreamSource } from "@/types/domain";
import { UnifiedSession } from "@/types/session";

import { apiDelete } from "@/shared/api/client";
import { apiGet } from "@/shared/api/client";
import { getStoredLanguage, UiLanguage } from "@/shared/lib/i18n";
import { SourceBadge } from "@/shared/ui/badges/SourceBadge";
import { Button } from "@/shared/ui/button";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

import { PosterCard } from "@/features/sessions/components/PosterCard";

import { HistoryFilterPanel } from "@/features/history/components/HistoryFilterPanel";
import { HistoryTable } from "@/features/history/components/HistoryTable";

const TEXT = {
  es: {
    pageTitle: "Historial",
    pageSubtitle: "Timeline de sesiones finalizadas e inactivas.",
    viewTable: "Tabla",
    viewCards: "Tarjetas",
    loading: "Cargando historial",
    noResults: "Sin sesiones encontradas",
    noResultsDesc: "Ajusta los filtros o el rango de fechas para buscar sesiones historicas.",
    untitled: "Sin titulo",
    page: "Pagina",
    of: "de",
    results: "resultados",
    previous: "Anterior",
    next: "Siguiente",
    edit: "Editar",
    cancelEdit: "Cancelar",
    deleteSelected: (n: number) => `Eliminar (${n})`,
    deleting: "Eliminando...",
    confirmDelete: (n: number) => `Eliminar ${n} sesion${n !== 1 ? "es" : ""}? Esta accion no se puede deshacer.`,
  },
  en: {
    pageTitle: "History",
    pageSubtitle: "Premium timeline for ended and stale sessions.",
    viewTable: "Table",
    viewCards: "Cards",
    loading: "Loading history",
    noResults: "No matching sessions",
    noResultsDesc: "Adjust filters or date range to find historical sessions.",
    untitled: "Untitled",
    page: "Page",
    of: "of",
    results: "results",
    previous: "Previous",
    next: "Next",
    edit: "Edit",
    cancelEdit: "Cancel",
    deleteSelected: (n: number) => `Delete (${n})`,
    deleting: "Deleting...",
    confirmDelete: (n: number) => `Delete ${n} session${n !== 1 ? "s" : ""}? This cannot be undone.`,
  },
} as const;

type ViewMode = "table" | "cards";

const PAGE_SIZE = 12;

function buildQuery(params: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value && value.trim().length > 0) {
      query.set(key, value);
    }
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}

function toIsoDateStart(date: string): string | undefined {
  if (!date) {
    return undefined;
  }
  return `${date}T00:00:00Z`;
}

function toIsoDateEnd(date: string): string | undefined {
  if (!date) {
    return undefined;
  }
  return `${date}T23:59:59Z`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "n/a" : date.toLocaleString();
}

export function HistoryPage() {
  const [lang, setLang] = useState<UiLanguage>(getStoredLanguage());
  useEffect(() => {
    const handler = (e: Event) => setLang((e as CustomEvent<{ language: UiLanguage }>).detail.language);
    window.addEventListener("streamfuse:language-changed", handler);
    return () => window.removeEventListener("streamfuse:language-changed", handler);
  }, []);
  const tx = TEXT[lang];

  const [rows, setRows] = useState<UnifiedSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Edit / selection state
  const [editMode, setEditMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);

  const [text, setText] = useState("");
  const [userName, setUserName] = useState("");
  const [source, setSource] = useState<"all" | StreamSource>("all");
  const [mediaType, setMediaType] = useState<"all" | MediaType>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const clearFilters = () => {
    setText("");
    setUserName("");
    setSource("all");
    setMediaType("all");
    setDateFrom("");
    setDateTo("");
  };

  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError(null);

      const query = buildQuery({
        user_name: userName || undefined,
        source: source === "all" ? undefined : source,
        media_type: mediaType === "all" ? undefined : mediaType,
        date_from: toIsoDateStart(dateFrom),
        date_to: toIsoDateEnd(dateTo),
        limit: "500",
      });

      const data = await apiGet<UnifiedSession[]>(`/sessions/history${query}`);
      setRows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchHistory();
  }, [userName, source, mediaType, dateFrom, dateTo]);

  useEffect(() => {
    const onRefresh = () => {
      void fetchHistory();
    };
    const onNewFilter = () => {
      clearFilters();
    };
    window.addEventListener("streamfuse:refresh", onRefresh);
    window.addEventListener("streamfuse:new-filter", onNewFilter);
    return () => {
      window.removeEventListener("streamfuse:refresh", onRefresh);
      window.removeEventListener("streamfuse:new-filter", onNewFilter);
    };
  }, [userName, source, mediaType, dateFrom, dateTo]);

  const filteredRows = useMemo(() => {
    if (!text.trim()) {
      return rows;
    }
    const query = text.trim().toLowerCase();
    return rows.filter((row) => {
      const haystack = [row.title, row.file_name, row.file_path, row.user_name, row.ip_address]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [rows, text]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);

  const pageRows = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredRows.slice(start, start + PAGE_SIZE);
  }, [filteredRows, currentPage]);

  useEffect(() => {
    setPage(1);
  }, [text, userName, source, mediaType, dateFrom, dateTo]);

  const chips = useMemo(() => {
    const items: Array<{ key: string; label: string }> = [];
    if (text) items.push({ key: "text", label: `text: ${text}` });
    if (userName) items.push({ key: "user", label: `user: ${userName}` });
    if (source !== "all") items.push({ key: "source", label: `source: ${source}` });
    if (mediaType !== "all") items.push({ key: "media", label: `media: ${mediaType}` });
    if (dateFrom) items.push({ key: "from", label: `from: ${dateFrom}` });
    if (dateTo) items.push({ key: "to", label: `to: ${dateTo}` });
    return items;
  }, [text, userName, source, mediaType, dateFrom, dateTo]);

  // --- edit mode helpers ---------------------------------------------------

  const enterEditMode = () => {
    setEditMode(true);
    setSelectedIds(new Set());
    setExpandedId(null);
  };

  const exitEditMode = () => {
    setEditMode(false);
    setSelectedIds(new Set());
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelectAll = (allIds: number[]) => {
    setSelectedIds((prev) => {
      const allSelected = allIds.every((id) => prev.has(id));
      if (allSelected) {
        // deselect all on current page
        const next = new Set(prev);
        allIds.forEach((id) => next.delete(id));
        return next;
      }
      // select all on current page
      const next = new Set(prev);
      allIds.forEach((id) => next.add(id));
      return next;
    });
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;
    const confirmed = window.confirm(tx.confirmDelete(selectedIds.size));
    if (!confirmed) return;

    try {
      setDeleting(true);
      await apiDelete("/sessions/bulk", { ids: Array.from(selectedIds) });
      exitEditMode();
      await fetchHistory();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6 min-h-[760px]">
      <header className="flex min-h-[72px] flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-3xl text-white">{tx.pageTitle}</h2>
          <p className="text-sm text-fg-muted">{tx.pageSubtitle}</p>
        </div>

        <div className="flex items-center gap-3">
          {editMode ? (
            <>
              <Button
                variant="destructive"
                onClick={() => { void handleDeleteSelected(); }}
                disabled={selectedIds.size === 0 || deleting}
              >
                {deleting ? tx.deleting : tx.deleteSelected(selectedIds.size)}
              </Button>
              <Button variant="outline" onClick={exitEditMode} disabled={deleting}>
                {tx.cancelEdit}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={enterEditMode}>
                {tx.edit}
              </Button>
              <div className="inline-flex rounded-xl border border-white/10 bg-card p-1">
                <button
                  type="button"
                  onClick={() => setViewMode("table")}
                  className={`rounded-lg px-3 py-1.5 text-sm ${viewMode === "table" ? "bg-white/[0.08] text-white" : "text-fg-muted"}`}
                >
                  {tx.viewTable}
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("cards")}
                  className={`rounded-lg px-3 py-1.5 text-sm ${viewMode === "cards" ? "bg-white/[0.08] text-white" : "text-fg-muted"}`}
                >
                  {tx.viewCards}
                </button>
              </div>
            </>
          )}
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[300px_1fr]">
        <HistoryFilterPanel
          userName={userName}
          source={source}
          mediaType={mediaType}
          dateFrom={dateFrom}
          dateTo={dateTo}
          text={text}
          onUserNameChange={setUserName}
          onSourceChange={setSource}
          onMediaTypeChange={setMediaType}
          onDateFromChange={setDateFrom}
          onDateToChange={setDateTo}
          onTextChange={setText}
          onClear={clearFilters}
        />

        <section className="space-y-4">
          {chips.length > 0 && !editMode ? (
            <div className="flex flex-wrap gap-2">
              {chips.map((chip) => (
                <span key={chip.key} className="rounded-full border border-white/20 bg-white/[0.04] px-3 py-1 text-xs text-fg-muted">
                  {chip.label}
                </span>
              ))}
            </div>
          ) : null}

          {loading ? <LoadingState title={tx.loading} /> : null}
          {!loading && error ? <ErrorState description={error} /> : null}
          {!loading && !error && filteredRows.length === 0 ? (
            <EmptyState title={tx.noResults} description={tx.noResultsDesc} />
          ) : null}

          {!loading && !error && filteredRows.length > 0 && viewMode === "table" ? (
            <HistoryTable
              sessions={pageRows}
              expandedId={expandedId}
              onToggleExpand={(id) => setExpandedId((current) => (current === id ? null : id))}
              editMode={editMode}
              selectedIds={selectedIds}
              onToggleSelect={toggleSelect}
              onToggleSelectAll={toggleSelectAll}
            />
          ) : null}

          {!loading && !error && filteredRows.length > 0 && viewMode === "cards" ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {pageRows.map((session) => {
                const isSelected = selectedIds.has(session.id);
                return (
                  <article
                    key={session.id}
                    className={`relative rounded-2xl border bg-card p-4 shadow-premium transition-colors ${
                      editMode ? "cursor-pointer" : ""
                    } ${isSelected ? "border-orange-500/60 bg-orange-500/10" : "border-white/10"}`}
                    onClick={editMode ? () => toggleSelect(session.id) : undefined}
                  >
                    {editMode ? (
                      <div className="absolute right-3 top-3 z-10" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(session.id)}
                          className="h-5 w-5 cursor-pointer accent-orange-500"
                        />
                      </div>
                    ) : null}
                    <PosterCard sessionId={session.id} title={session.title || "poster"} />
                    <div className="mt-3 flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium text-white">{session.title || session.file_name || tx.untitled}</p>
                        <p className="text-xs text-fg-muted">{session.user_name} - {formatDate(session.updated_at)}</p>
                      </div>
                      <SourceBadge source={session.source} />
                    </div>
                    <p className="mt-2 truncate text-xs text-fg-muted">{session.file_path || "n/a"}</p>
                  </article>
                );
              })}
            </div>
          ) : null}

          {!loading && !error && filteredRows.length > 0 ? (
            <div className="flex items-center justify-between rounded-xl border border-white/10 bg-card px-4 py-3">
              <p className="text-sm text-fg-muted">
                {tx.page} {currentPage} / {totalPages} - {filteredRows.length} {tx.results}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={currentPage <= 1}>
                  {tx.previous}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                  disabled={currentPage >= totalPages}
                >
                  {tx.next}
                </Button>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
