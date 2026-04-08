import { ChangeEvent } from "react";

import { MediaType, StreamSource } from "@/types/domain";

import { Button } from "@/shared/ui/button";

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
  return (
    <section className="rounded-2xl border border-white/10 bg-card p-4 shadow-premium">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs text-fg-muted">
          User
          <input
            value={userQuery}
            onChange={(event: ChangeEvent<HTMLInputElement>) => onUserQueryChange(event.target.value)}
            placeholder="Search user"
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

        <div className="flex items-end justify-end">
          <Button variant="ghost" onClick={onClear}>
            Clear Filters
          </Button>
        </div>
      </div>
    </section>
  );
}
