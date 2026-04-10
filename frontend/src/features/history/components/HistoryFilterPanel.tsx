import { ChangeEvent } from "react";

import { MediaType, StreamSource } from "@/types/domain";

import { Button } from "@/shared/ui/button";

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
  return (
    <aside className="rounded-2xl border border-white/10 bg-card p-4 shadow-premium">
      <h3 className="font-display text-lg text-white">Filters</h3>

      <div className="mt-4 space-y-3">
        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          Search text
          <input
            value={text}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onTextChange(event.target.value)}
            placeholder="title, path, ip"
            className="rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          User
          <input
            value={userName}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onUserNameChange(event.target.value)}
            placeholder="alice"
            className="rounded-lg border border-white/15 bg-white/[0.03] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          Source
          <select
            value={source}
            onChange={(event) => onSourceChange(event.target.value as "all" | StreamSource)}
            className="rounded-lg border border-white/15 bg-[#0b1528] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          >
            <option value="all">All sources</option>
            <option value="tautulli">Tautulli</option>
            <option value="sftpgo">SFTPGo</option>
            <option value="samba">Samba</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          Media Type
          <select
            value={mediaType}
            onChange={(event) => onMediaTypeChange(event.target.value as "all" | MediaType)}
            className="rounded-lg border border-white/15 bg-[#0b1528] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          >
            <option value="all">All media</option>
            <option value="movie">Movie</option>
            <option value="episode">Episode</option>
            <option value="live">Live</option>
            <option value="file_transfer">File transfer</option>
            <option value="other">Other</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          From
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => onDateFromChange(event.target.value)}
            className="rounded-lg border border-white/15 bg-[#0b1528] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          To
          <input
            type="date"
            value={dateTo}
            onChange={(event) => onDateToChange(event.target.value)}
            className="rounded-lg border border-white/15 bg-[#0b1528] px-3 py-2 text-sm text-white outline-none focus:border-primary/60"
          />
        </label>

        <Button variant="ghost" className="w-full" onClick={onClear}>
          Clear Filters
        </Button>
      </div>
    </aside>
  );
}



