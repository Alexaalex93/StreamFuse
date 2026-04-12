const AUTH_TOKEN_KEY = "streamfuse_auth_token";

export class ApiError extends Error {
  status: number;
  body: string;

  constructor(status: number, body: string) {
    super(body || `API error: ${status}`);
    this.status = status;
    this.body = body;
  }
}

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

export function getAuthToken(): string | null {
  try {
    return window.localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearAuthToken(): void {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

function resolveRequestUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  if (path.startsWith("/api/")) {
    return path;
  }
  return `${API_BASE}${path}`;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(resolveRequestUrl(path), {
    ...init,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(response.status, errorText || `API error: ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: "GET" });
}

export async function apiGetWithFallback<T>(paths: string[]): Promise<T> {
  let lastError: unknown;

  for (const path of paths) {
    try {
      return await apiGet<T>(path);
    } catch (error) {
      lastError = error;
      if (error instanceof ApiError && error.status === 404) {
        continue;
      }
      throw error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error("No API endpoint available");
}

export async function apiPut<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function apiPost<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
