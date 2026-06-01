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
    me: () => request<{ id: string; email: string; display_name: string; role: string; created_at: string }>("/auth/me"),
    logout: () => request("/auth/logout", { method: "POST" }),
  },
  dashboard: {
    user: () => request<import("./types").UserDashboardData>("/dashboard/user"),
    admin: () => request<import("./types").AdminDashboardData>("/dashboard/admin"),
  },
};
