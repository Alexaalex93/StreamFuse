const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

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