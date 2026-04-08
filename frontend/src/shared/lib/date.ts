export function parseApiDate(value: string | null | undefined): Date | null {
  if (!value) {
    return null;
  }

  const hasTimezone = /[zZ]|[+-]\d\d:\d\d$/.test(value);
  const normalized = hasTimezone ? value : `${value}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatLocalTime(value: string | null | undefined): string {
  const date = parseApiDate(value);
  if (!date) {
    return "unknown";
  }
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatLocalDateTime(value: string | null | undefined): string {
  const date = parseApiDate(value);
  if (!date) {
    return "n/a";
  }
  return date.toLocaleString();
}

export function relativeFromNow(value: string | null | undefined): string {
  const date = parseApiDate(value);
  if (!date) {
    return "n/a";
  }

  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) {
    return "just now";
  }
  if (mins < 60) {
    return `${mins}m ago`;
  }
  return `${Math.floor(mins / 60)}h ago`;
}
