import type {
  AdminDashboardData,
  AdminUserItem,
  AttributionData,
  ChannelConfigItem,
  KeywordConfigItem,
  ProductAliasItem,
  ProductConfigItem,
  ProductDetailChangeRequestItem,
  ProductSpecTemplateItem,
  ProductResolutionCandidate,
  VideoProductMapping,
  PipelineHealthData,
  ProductDetail,
  ProductComment,
  SearchResponse,
  LogFileListResponse,
  LogTailResponse,
  FavoriteProductItem,
  ProductFavoriteStatus,
  TopProduct,
  UserDashboardData,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("access_token");
}

function formatErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) return String(item.msg);
        return null;
      })
      .filter(Boolean)
      .join(", ") || fallback;
  }
  if (detail && typeof detail === "object" && "msg" in detail) {
    return String(detail.msg);
  }
  return fallback;
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
    throw { status: res.status, detail: formatErrorDetail(err.detail, res.statusText || "Request failed") };
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
    comments: (productId: string, limit = 30) =>
      request<ProductComment[]>(`/products/${productId}/comments?limit=${limit}`),
    submitDetails: (productId: string, data: { proposed_specs?: Record<string, unknown>; proposed_description?: string }) =>
      request<{ request_id: string; status: string }>(`/products/${productId}/details/requests`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    favorites: {
      list: () => request<FavoriteProductItem[]>("/products/favorites"),
      status: (productId: string) =>
        request<ProductFavoriteStatus>(`/products/${productId}/favorite`),
      add: (productId: string) =>
        request<ProductFavoriteStatus>(`/products/${productId}/favorite`, { method: "POST" }),
      remove: (productId: string) =>
        request<ProductFavoriteStatus>(`/products/${productId}/favorite`, { method: "DELETE" }),
    },
  },

  search: (q: string, category = "", limit = 20, options: RequestInit = {}) =>
    request<SearchResponse>(`/search?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}&limit=${limit}`, options),

  admin: {
    channels: {
      list: () => request<ChannelConfigItem[]>("/admin/channels"),
      create: (data: { channel_url: string }) =>
        request<ChannelConfigItem>("/admin/channels", { method: "POST", body: JSON.stringify(data) }),
      update: (id: string, data: { channel_name?: string; channel_url?: string; channel_handle?: string; subscriber_count?: number; is_active?: boolean }) =>
        request<ChannelConfigItem>(`/admin/channels/${id}`, { method: "PUT", body: JSON.stringify(data) }),
      crawl: (id: string, data: { lookback_days: number; preferred_mode?: "auto" | "api" | "ytdlp" }) =>
        request<{ run_id?: string; crawl_mode: string; quota_remaining: number; lookback_days: number }>(`/admin/channels/${id}/crawl`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
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
    products: {
      list: () => request<ProductConfigItem[]>("/admin/products"),
      create: (data: { product_id?: string; product_name: string; brand?: string; category?: string; release_year?: number }) =>
        request<ProductConfigItem>("/admin/products", { method: "POST", body: JSON.stringify(data) }),
      aliases: () => request<ProductAliasItem[]>("/admin/products/aliases"),
      createAlias: (data: { product_id: string; alias_text: string; alias_type?: string }) =>
        request<ProductAliasItem>("/admin/products/aliases", { method: "POST", body: JSON.stringify(data) }),
      removeAlias: (aliasId: string) => request<void>(`/admin/products/aliases/${aliasId}`, { method: "DELETE" }),
      templates: () => request<ProductSpecTemplateItem[]>("/admin/products/templates"),
      createTemplate: (data: { category: string; spec_key: string; display_label: string; value_type: "string" | "number" | "boolean"; unit?: string }) =>
        request<ProductSpecTemplateItem>("/admin/products/templates", { method: "POST", body: JSON.stringify(data) }),
      removeTemplate: (category: string, specKey: string) =>
        request<void>(`/admin/products/templates/${encodeURIComponent(category)}/${encodeURIComponent(specKey)}`, { method: "DELETE" }),
      detailRequests: (status = "pending") => request<ProductDetailChangeRequestItem[]>(`/admin/products/detail-requests?status=${encodeURIComponent(status)}`),
      reviewDetailRequest: (id: string, action: "approve" | "reject") =>
        request<{ request_id: string; status: string }>(`/admin/products/detail-requests/${id}/review`, {
          method: "POST",
          body: JSON.stringify({ action }),
        }),
      candidates: (status = "pending") => request<ProductResolutionCandidate[]>(`/admin/products/resolution-candidates?status=${encodeURIComponent(status)}`),
      reviewCandidate: (id: string, product_id: string, alias_text?: string, sentiment_label?: "POSITIVE" | "NEGATIVE" | "NEUTRAL") =>
        request(`/admin/products/resolution-candidates/${id}/review`, {
          method: "POST",
          body: JSON.stringify({ product_id, alias_text, sentiment_label }),
        }),
      rejectCandidate: (id: string) => request(`/admin/products/resolution-candidates/${id}/reject`, { method: "POST" }),
      videoMappings: () => request<VideoProductMapping[]>("/admin/products/video-mappings"),
      overrideVideoMapping: (videoId: string, product_id: string, role: "primary" | "secondary" = "primary") =>
        request(`/admin/products/video-mappings/${videoId}`, {
          method: "PUT",
          body: JSON.stringify({ product_id, role }),
        }),
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
    logs: {
      list: () => request<LogFileListResponse>("/admin/logs"),
      tail: (path: string, lines = 200) =>
        request<LogTailResponse>(`/admin/logs/tail?path=${encodeURIComponent(path)}&lines=${lines}`),
    },
    users: {
      list: () => request<AdminUserItem[]>("/admin/users"),
      create: (data: { email: string; password: string; display_name: string; role: "user" | "admin" }) =>
        request<AdminUserItem>("/admin/users", { method: "POST", body: JSON.stringify(data) }),
      update: (id: string, data: { display_name?: string; role?: "user" | "admin"; is_active?: boolean; password?: string }) =>
        request<AdminUserItem>(`/admin/users/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    },
  },
};
