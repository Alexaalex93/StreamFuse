function resolveApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE ?? "/api/v1";

  if (!/^https?:\/\//.test(raw)) {
    return raw;
  }

  try {
    const parsed = new URL(raw);
    const isLocalHost = parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1";
    if (!isLocalHost) {
      return raw;
    }

    const browserHost = window.location.hostname;
    if (!browserHost) {
      return raw;
    }

    parsed.hostname = browserHost;
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return raw;
  }
}

const API_BASE = resolveApiBase();

export function getApiBase(): string {
  return API_BASE;
}

export function getBackendBase(): string {
  if (/^https?:\/\//.test(API_BASE)) {
    return API_BASE.replace(/\/api\/v1\/?$/, "");
  }
  return "";
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `API error: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: "GET" });
}

export async function apiPut<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}