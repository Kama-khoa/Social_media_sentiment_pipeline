# CLAUDE.md — frontend/

## Trạng thái hiện tại (2026-06-01)

Phase 5 MVP — các trang dashboard đã triển khai xong, sẵn sàng chạy và demo.

| File | Trạng thái | Nhiệm vụ |
|---|---|---|
| `app/layout.tsx` | Hoàn thành | Root layout, bọc `<Providers>` |
| `app/page.tsx` | Hoàn thành | Redirect `/` → `/dashboard` |
| `app/(auth)/layout.tsx` | Hoàn thành | Layout centered cho trang login/register |
| `app/(auth)/login/page.tsx` | Hoàn thành | Form đăng nhập, hint demo credentials |
| `app/(auth)/register/page.tsx` | Hoàn thành | Form đăng ký tài khoản user |
| `app/(app)/layout.tsx` | Hoàn thành | Layout với Sidebar + Header, route guard redirect về `/login` |
| `app/(app)/dashboard/page.tsx` | Hoàn thành | Chọn `UserDashboard` / `AdminDashboard` theo role |
| `components/Providers.tsx` | Hoàn thành | Client wrapper cho `AuthProvider` |
| `components/layout/Sidebar.tsx` | Hoàn thành | Nav cố định 224px, menu Admin ẩn với user thường |
| `components/layout/Header.tsx` | Hoàn thành | Top bar cố định, avatar, nút logout |
| `components/dashboard/UserDashboard.tsx` | Hoàn thành (mock) | Category stats, top products table, causal events |
| `components/dashboard/AdminDashboard.tsx` | Hoàn thành (mock) | Pipeline status, DAG runs, quick stats, attention items |
| `components/shared/ControversyBadge.tsx` | Hoàn thành | Badge high/medium/low controversy |
| `lib/api-client.ts` | Hoàn thành | Fetch wrapper với Bearer token từ sessionStorage |
| `lib/auth-context.tsx` | Hoàn thành | React Context: user, token, login(), logout() |
| `lib/types.ts` | Hoàn thành | TypeScript interfaces cho toàn bộ API response |
| `app/(app)/analytics/**` | Chưa tạo | Search, top products, product detail, attribution |
| `app/(app)/admin/**` | Chưa tạo | CRUD channel/keyword, pipeline health |

---

## Tech stack thực tế

| Thành phần | Phiên bản | Ghi chú |
|---|---|---|
| Next.js | 16.2.6 | App Router, TypeScript |
| React | 19.x | |
| Tailwind CSS | 4.x | Dùng `@import "tailwindcss"` trong CSS, **không** có `tailwind.config.js` |
| PostCSS | `@tailwindcss/postcss` | Plugin riêng cho Tailwind v4 |
| TypeScript | 5.x | Strict mode |
| Node.js | 20.9+ | |

---

## Chạy frontend

### Yêu cầu

- Node.js 20.9+
- Backend FastAPI đang chạy tại `http://localhost:8000`

### Khởi động

```powershell
cd frontend
npm install   # chỉ lần đầu
npm run dev
```

Frontend chạy tại `http://localhost:3000`.

### Build production

```powershell
cd frontend
npm run build
npm start
```

### Kiểm tra TypeScript

```powershell
cd frontend
npx tsc --noEmit
```

---

## Biến môi trường

Tạo file `frontend/.env.local` nếu cần override:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Mặc định `api-client.ts` fallback về `http://localhost:8000` nếu biến không được set.

**Lưu ý:** Chỉ các biến prefix `NEXT_PUBLIC_` mới được bundle vào client bundle. Không đặt GCP credentials, JWT secret, hay Airflow credentials vào file này.

---

## Cấu trúc thư mục thực tế

```text
frontend/
├── .env.local              ← NEXT_PUBLIC_API_BASE_URL (tạo nếu cần)
├── next.config.ts
├── postcss.config.mjs      ← @tailwindcss/postcss
├── tsconfig.json
├── package.json
├── app/
│   ├── globals.css         ← @import "tailwindcss"; body base styles
│   ├── layout.tsx          ← Root layout: html/body + <Providers>
│   ├── page.tsx            ← redirect("/dashboard")
│   ├── (auth)/             ← Route group: không có sidebar
│   │   ├── layout.tsx      ← Centered full-screen layout
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   └── (app)/              ← Route group: có sidebar + header, cần auth
│       ├── layout.tsx      ← Route guard + Sidebar + Header
│       ├── dashboard/page.tsx
│       ├── analytics/      ← TODO: search, top-products, products/[id]
│       └── admin/          ← TODO: channels, keywords, pipeline-health
├── components/
│   ├── Providers.tsx       ← "use client" wrapper cho AuthProvider
│   ├── layout/
│   │   ├── Sidebar.tsx     ← Nav cố định bên trái, w-56
│   │   └── Header.tsx      ← Top bar cố định, ml-56
│   ├── dashboard/
│   │   ├── UserDashboard.tsx
│   │   └── AdminDashboard.tsx
│   └── shared/
│       └── ControversyBadge.tsx
└── lib/
    ├── api-client.ts       ← fetch wrapper, tự đính Bearer token
    ├── auth-context.tsx    ← React Context: AuthProvider + useAuth hook
    └── types.ts            ← TypeScript interfaces cho API responses
```

---

## Auth flow

```
Người dùng truy cập bất kỳ route (app)/
    │
    ▼
(app)/layout.tsx kiểm tra useAuth()
    ├── isLoading = true → hiển thị spinner
    ├── user = null → router.replace("/login")
    └── user tồn tại → render Sidebar + Header + children

Trang login:
    1. User nhập email/password → gọi api.auth.login()
    2. API trả { access_token, role }
    3. sessionStorage.setItem("access_token", token)
    4. Gọi api.auth.me() → lấy UserInfo
    5. Set user state → router.push("/dashboard")

Reload trang:
    1. AuthProvider mount → đọc sessionStorage
    2. Nếu có token → gọi /auth/me để verify
    3. Nếu token hết hạn → /auth/me trả 401 → user = null → redirect login
```

---

## API Client

File: [lib/api-client.ts](lib/api-client.ts)

Tất cả call API đi qua hàm `request<T>()`:
- Tự đọc token từ `sessionStorage`
- Gắn `Authorization: Bearer <token>`
- Throw object `{ status, detail }` khi response không OK

```typescript
import { api } from "@/lib/api-client";

// Trong component:
const data = await api.dashboard.user();
const data = await api.dashboard.admin();
const result = await api.auth.login(email, password);
await api.auth.logout();
```

### Mở rộng API client

Để thêm endpoint mới, bổ sung vào `api` object:

```typescript
// lib/api-client.ts
export const api = {
  // ...hiện có...
  products: {
    top: (category: string) =>
      request<TopProduct[]>(`/products/top/${category}`),
    detail: (id: string) =>
      request<ProductDetail>(`/products/${id}`),
  },
  admin: {
    channels: {
      list: () => request("/admin/channels"),
      create: (data: unknown) => request("/admin/channels", { method: "POST", body: JSON.stringify(data) }),
      delete: (id: string) => request(`/admin/channels/${id}`, { method: "DELETE" }),
    },
  },
};
```

---

## Routing và Route Groups

| Route group | Layout | Áp dụng cho |
|---|---|---|
| `(auth)` | Centered full-screen, không sidebar | `/login`, `/register` |
| `(app)` | Sidebar + Header, route guard | `/dashboard`, `/analytics/*`, `/admin/*` |

Route group là thư mục có tên trong ngoặc `()` — không ảnh hưởng đến URL path.

---

## Dashboard theo role

File: [app/(app)/dashboard/page.tsx](app/(app)/dashboard/page.tsx)

```typescript
const { user } = useAuth();
return user.role === "admin" ? <AdminDashboard /> : <UserDashboard />;
```

- **UserDashboard**: Fetch `/dashboard/user` → category stats (4 card), top products table, causal events
- **AdminDashboard**: Fetch `/dashboard/admin` → pipeline status cards, DAG runs table, quick stats, attention items

---

## Màu sắc và design system

Palette light-muted, không dùng dark mode trong MVP:

| Vai trò | Màu accent | Dùng cho |
|---|---|---|
| User | `indigo-600` | Nav active, button, avatar |
| Admin | `violet-600` | Admin badge, admin button, admin accent |
| Background | `slate-50` | Body, card background |
| Border | `slate-200` | Card border, divider |
| Text chính | `slate-800` | Heading, label |
| Text phụ | `slate-500` | Subtext, metadata |
| Positive | `emerald-*` | Positive sentiment, success state |
| Negative | `rose-*` | Negative sentiment, error, warning |
| Neutral | `amber-*` | Medium controversy |

---

## Tailwind CSS v4 — lưu ý quan trọng

Dự án dùng **Tailwind CSS v4** với cú pháp khác v3:

```css
/* globals.css — ĐÚNG cho v4 */
@import "tailwindcss";

/* SAI — đây là cú pháp v3 */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Plugin PostCSS là `@tailwindcss/postcss`, không phải `tailwindcss` cũ. **Không có file `tailwind.config.js`** — config nằm trực tiếp trong CSS nếu cần.

---

## Thêm trang mới

### Trang analytics (user)

```typescript
// app/(app)/analytics/top-products/page.tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";

export default function TopProductsPage() {
  const [data, setData] = useState(null);
  useEffect(() => { api.products.top("all").then(setData); }, []);
  // ...
}
```

### Trang admin

```typescript
// app/(app)/admin/channels/page.tsx
"use client";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";

export default function AdminChannelsPage() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user && user.role !== "admin") router.replace("/dashboard");
  }, [user]);

  // ...
}
```

Sidebar tự động hiện/ẩn menu Admin dựa vào `user.role`. Nhưng **luôn** phải check role ở trang admin vì người dùng có thể nhập URL trực tiếp.

---

## Sidebar navigation

File: [components/layout/Sidebar.tsx](components/layout/Sidebar.tsx)

```
Sidebar (w-56, fixed left)
├── Logo: "SentimentIQ"
├── Nav User (mọi role):
│   ├── Dashboard → /dashboard
│   ├── Tìm kiếm → /analytics/search (TODO)
│   └── Bảng xếp hạng → /analytics/top-products (TODO)
├── Nav Admin (chỉ role=admin):
│   ├── Kênh YouTube → /admin/channels (TODO)
│   ├── Từ khóa → /admin/keywords (TODO)
│   └── Vận hành Pipeline → /admin/pipeline-health (TODO)
└── Bottom: Avatar + display_name + role + logout
```

---

## Lưu ý kỹ thuật

- **`"use client"` directive**: Tất cả component dùng hooks (useEffect, useAuth, useRouter) phải có directive này ở đầu file. `app/(app)/layout.tsx` là client component vì dùng `useAuth`.
- **Providers.tsx pattern**: `app/layout.tsx` là server component — không thể trực tiếp dùng `AuthProvider` (context). Giải pháp: `Providers.tsx` là client component, được import vào root layout để bọc `AuthProvider`.
- **sessionStorage**: Không tồn tại ở server-side. `api-client.ts` kiểm tra `typeof window === "undefined"` trước khi đọc.
- **Route guard**: Logic redirect nằm ở `(app)/layout.tsx` — không cần lặp lại ở từng page.
- **TypeScript paths**: `@/` alias trỏ đến `frontend/` (configured trong `tsconfig.json`).
