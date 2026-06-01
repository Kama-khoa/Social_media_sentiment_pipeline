import type {
  AdminDashboardData,
  AttributionData,
  ChannelConfigItem,
  KeywordConfigItem,
  PipelineHealthData,
  ProductDetail,
  SearchResponse,
  TopProduct,
  UserDashboardData,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("access_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw { status: res.status, detail: err.detail ?? "Request failed" };
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; token_type: string; role: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    register: (email: string, password: string, display_name: string) =>
      request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, display_name }),
      }),
    me: () =>
      request<{ id: string; email: string; display_name: string; role: string; created_at: string }>("/auth/me"),
    logout: () => request("/auth/logout", { method: "POST" }),
  },

  dashboard: {
    user: () => request<UserDashboardData>("/dashboard/user"),
    admin: () => request<AdminDashboardData>("/dashboard/admin"),
  },

  products: {
    top: (category: string = "all", limit = 20) =>
      request<TopProduct[]>(`/products/top/${category}?limit=${limit}`),
    aspects: (productId: string) =>
      request<ProductDetail>(`/products/${productId}/aspects`),
    attribution: (productId: string) =>
      request<AttributionData>(`/products/${productId}/attribution`),
  },

  search: (q: string, category = "", limit = 20) =>
    request<SearchResponse>(`/search?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}&limit=${limit}`),

  admin: {
    channels: {
      list: () => request<ChannelConfigItem[]>("/admin/channels"),
      create: (data: { channel_id: string; channel_name: string; channel_url?: string; channel_handle?: string; subscriber_count?: number }) =>
        request<ChannelConfigItem>("/admin/channels", { method: "POST", body: JSON.stringify(data) }),
      update: (id: string, data: { channel_name?: string; channel_url?: string; channel_handle?: string; subscriber_count?: number }) =>
        request<ChannelConfigItem>(`/admin/channels/${id}`, { method: "PUT", body: JSON.stringify(data) }),
      remove: (id: string) => request<void>(`/admin/channels/${id}`, { method: "DELETE" }),
    },
    keywords: {
      list: () => request<KeywordConfigItem[]>("/admin/keywords"),
      create: (data: { keyword_text: string; search_cluster?: string }) =>
        request<KeywordConfigItem>("/admin/keywords", { method: "POST", body: JSON.stringify(data) }),
      update: (id: string, data: { keyword_text?: string; search_cluster?: string }) =>
        request<KeywordConfigItem>(`/admin/keywords/${id}`, { method: "PUT", body: JSON.stringify(data) }),
      remove: (id: string) => request<void>(`/admin/keywords/${id}`, { method: "DELETE" }),
    },
    pipeline: {
      health: () => request<PipelineHealthData>("/admin/pipeline/health"),
      dags: () => request<unknown>("/admin/pipeline/dags"),
      runs: (dagId: string, limit = 5) => request<unknown>(`/admin/pipeline/dags/${dagId}/runs?limit=${limit}`),
      tasks: (dagId: string, runId: string) =>
        request<unknown>(`/admin/pipeline/dags/${dagId}/runs/${runId}/tasks`),
      trigger: (dagId: string) =>
        request<unknown>(`/admin/pipeline/dags/${dagId}/trigger`, { method: "POST" }),
      metrics: () => request<unknown>("/admin/pipeline/metrics"),
    },
  },
};
