// API 客户端：统一封装对 FastAPI 后端的调用

import type { Chart, ListResponse, Stats } from "./types";

const BASE = "";  // 走 Next rewrites 代理到 127.0.0.1:8701

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  const text = await res.text();
  let data: any = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`服务返回非 JSON（${res.status}）`);
  }
  if (!res.ok) {
    const msg =
      data?.detail && Array.isArray(data.detail)
        ? data.detail.map((d: any) => d.msg).join("；")
        : data?.detail || data?.error || `请求失败（${res.status}）`;
    throw new Error(msg);
  }
  return data as T;
}

export interface ListParams {
  q?: string;
  gender?: string;
  star?: string;
  tag?: string;
  page?: number;
  size?: number;
  sort?: string;
}

export function buildQuery(p: ListParams): string {
  const sp = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => request<{ ok: boolean }>("/api/health"),

  engine: () =>
    request<{ ok: boolean; iztro?: string; license?: string }>("/api/engine"),

  list: (p: ListParams = {}) =>
    request<ListResponse>("/api/charts" + buildQuery(p)),

  get: (id: number) =>
    request<{ ok: boolean; chart: Chart }>(`/api/charts/${id}`),

  create: (body: Record<string, unknown>) =>
    request<{ ok: boolean; id: number; chart: Chart }>("/api/charts", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  update: (id: number, body: Record<string, unknown>) =>
    request<{ ok: boolean; chart: Chart }>(`/api/charts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  remove: (id: number) =>
    request<{ ok: boolean }>(`/api/charts/${id}`, { method: "DELETE" }),

  restore: (id: number) =>
    request<{ ok: boolean }>(`/api/charts/${id}/restore`, { method: "POST" }),

  stats: () => request<{ ok: boolean; stats: Stats }>("/api/stats"),

  audit: (limit = 30) =>
    request<{ ok: boolean; items: any[] }>(`/api/audit?limit=${limit}`),
};
