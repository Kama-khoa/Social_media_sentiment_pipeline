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
    CategoryStat,
    UserDashboardData,
    PipelineOpsSeries,
    DagRunSummary,
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
        stats: () => request<CategoryStat[]>("/products/stats"),
        aspects: (productId: string) =>
            request<ProductDetail>(`/products/${productId}/aspects`),
        attribution: (productId: string) =>
            request<AttributionData>(`/products/${productId}/attribution`),
        comments: (productId: string, limit = 10) =>
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
            quota: () => request<{ search_remaining: number }>("/admin/channels/quota"),
            list: () => request<ChannelConfigItem[]>("/admin/channels"),
            create: (data: { channel_url: string }) =>
                request<ChannelConfigItem>("/admin/channels", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: { channel_name?: string; channel_url?: string; channel_handle?: string; subscriber_count?: number; is_active?: boolean }) =>
                request<ChannelConfigItem>(`/admin/channels/${id}`, { method: "PUT", body: JSON.stringify(data) }),
            crawl: (id: string, data: { lookback_days: number; preferred_mode?: "auto" | "api" | "ytdlp" }) =>
                request<{ dag_id?: string; run_id?: string; crawl_mode: string; quota_remaining: number; lookback_days: number }>(`/admin/channels/${id}/crawl`, {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            remove: (id: string) => request<void>(`/admin/channels/${id}`, { method: "DELETE" }),
            suggestions: {
                list: (min_video_count = 2, limit = 20) => request<any[]>(`/admin/channels/suggestions?min_video_count=${min_video_count}&limit=${limit}`),
                approve: (data: { channel_id: string; channel_name: string; channel_url?: string; channel_handle?: string }) =>
                    request<any>("/admin/channels/suggestions/approve", { method: "POST", body: JSON.stringify(data) }),
            },
        },
        keywords: {
            list: (params?: { product_id?: string; is_active?: boolean; limit?: number; offset?: number }) => {
                const query = new URLSearchParams();
                if (params?.product_id) query.append("product_id", params.product_id);
                if (params?.is_active !== undefined) query.append("is_active", String(params.is_active));
                if (params?.limit) query.append("limit", String(params.limit));
                if (params?.offset !== undefined) query.append("offset", String(params.offset));
                const qs = query.toString() ? `?${query.toString()}` : "";
                return request<KeywordConfigItem[]>(`/admin/keywords${qs}`);
            },
            create: (data: { keyword_text: string; search_cluster?: string }) =>
                request<KeywordConfigItem>("/admin/keywords", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: { keyword_text?: string; search_cluster?: string }) =>
                request<KeywordConfigItem>(`/admin/keywords/${id}`, { method: "PUT", body: JSON.stringify(data) }),
            remove: (id: string) => request<void>(`/admin/keywords/${id}`, { method: "DELETE" }),
            suggest: (product_id: string) => request<any[]>("/admin/keywords/suggest", { method: "POST", body: JSON.stringify({ product_id }) }),
            bulkLink: (data: { keyword_ids: string[]; product_id: string }) => request<any>("/admin/keywords/bulk-link", { method: "POST", body: JSON.stringify(data) }),
        },
        products: {
            list: (params?: { limit?: number; offset?: number; category?: string; q?: string }) => {
                const query = new URLSearchParams();
                if (params?.limit) query.append("limit", String(params.limit));
                if (params?.offset !== undefined) query.append("offset", String(params.offset));
                if (params?.category) query.append("category", params.category);
                if (params?.q) query.append("q", params.q);
                const qs = query.toString() ? `?${query.toString()}` : "";
                return request<ProductConfigItem[]>(`/admin/products${qs}`);
            },
            count: (params?: { category?: string; q?: string }) => {
                const query = new URLSearchParams();
                if (params?.category) query.append("category", params.category);
                if (params?.q) query.append("q", params.q);
                const qs = query.toString() ? `?${query.toString()}` : "";
                return request<{ count: number }>(`/admin/products/count${qs}`);
            },
            create: (data: { product_id?: string; product_name: string; brand?: string; category?: string; release_year?: number }) =>
                request<ProductConfigItem>("/admin/products", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: { product_name?: string; brand?: string; category?: string; release_year?: number; is_active?: boolean }) =>
                request<ProductConfigItem>(`/admin/products/${id}`, { method: "PUT", body: JSON.stringify(data) }),
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
            reviewDetailRequest: (id: string, action: "approve" | "reject" | "processing") =>
                request<{ request_id: string; status: string }>(`/admin/products/detail-requests/${id}/review`, {
                    method: "POST",
                    body: JSON.stringify({ action }),
                }),
            candidateCounts: () => request<Record<string, number>>("/admin/products/resolution-candidates/counts"),
            candidates: (status = "pending", page = 1, limit = 20) => request<ProductResolutionCandidate[]>(`/admin/products/resolution-candidates?status=${encodeURIComponent(status)}&page=${page}&limit=${limit}`),
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
            sync: (productId: string) =>
                request<{ message: string; product_id: string }>(`/admin/products/${productId}/sync`, { method: "POST" }),
            crawl: (productId: string, useYtdlp = false) =>
                request<{ status: string; task_id?: string; message: string }>(`/admin/products/${productId}/crawl?use_ytdlp=${useYtdlp}`, {
                    method: "POST",
                }),
            crawlTaskStatus: (taskId: string) =>
                request<{ task_id: string; status: string; progress: number; message: string; error?: string }>(`/admin/products/crawl-tasks/${taskId}`),
        },
        pipeline: {
            health: () => request<PipelineHealthData>("/admin/pipeline/health"),
            dags: () => request<unknown>("/admin/pipeline/dags"),
            runs: (dagId: string, limit = 5) => request<unknown>(`/admin/pipeline/dags/${dagId}/runs?limit=${limit}`),
            tasks: (dagId: string, runId: string) =>
                request<unknown>(`/admin/pipeline/dags/${dagId}/runs/${runId}/tasks`),
            taskLog: (dagId: string, runId: string, taskId: string, tryNumber: number = 1) =>
                request<{ content: string }>(`/admin/pipeline/dags/${dagId}/runs/${runId}/tasks/${taskId}/logs/${tryNumber}`),
            trigger: (dagId: string) =>
                request<unknown>(`/admin/pipeline/dags/${dagId}/trigger`, { method: "POST" }),
            metrics: () => request<unknown>("/admin/pipeline/metrics"),
            series: () => request<PipelineOpsSeries>("/admin/pipeline/series"),
        },
        backfill: {
            status: () => request<any>("/admin/backfill/status"),
            triggerHistorical: (limit_channels = 5) => request<any>("/admin/backfill/historical", { method: "POST", body: JSON.stringify({ limit_channels }) }),
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
