import type { ApiErrorPayload } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("owlclaw_token");
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    const payload = (await res.json().catch(() => ({}))) as Partial<ApiErrorPayload>;
    throw new ApiError(res.status, payload.error?.code ?? "http_error", payload.error?.message ?? "Request failed");
  }

  return (await res.json()) as T;
}
