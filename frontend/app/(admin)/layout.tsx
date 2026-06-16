"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { AdminSidebar } from "@/components/layout/AdminSidebar";
import { Header } from "@/components/layout/Header";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [hash, setHash] = useState("");

  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        router.replace("/login");
      } else if (user.role !== "admin") {
        router.replace("/");
      }
    }
  }, [user, isLoading, router]);

  useEffect(() => {
    const syncHash = () => setHash(window.location.hash);
    syncHash();
    window.addEventListener("hashchange", syncHash);
    window.addEventListener("popstate", syncHash);
    return () => {
      window.removeEventListener("hashchange", syncHash);
      window.removeEventListener("popstate", syncHash);
    };
  }, [pathname]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user || user.role !== "admin") return null;

  const titleMap: Record<string, string> = {
    "/admin": "Tổng quan phân tích",
    "/admin/keywords": "Quản lý từ khóa",
    "/admin/channels": "Quản lý kênh",
    "/admin/products": "Quản lý sản phẩm",
    "/admin/products/aliases": "Tên gọi khác",
    "/admin/products/candidates": "Duyệt ánh xạ SP",
    "/admin/products/spec-templates": "Mẫu thông số",
    "/admin/users": "Quản lý tài khoản",
    "/admin/logs": "Quản lý log pipeline",
    "/admin/airflow": "Tình trạng Pipeline",
    "/admin/airflow/runs": "Lịch sử DAG Runs",
    "/admin/airflow/ops": "Chỉ số vận hành",
  };
  const title = titleMap[`${pathname}${hash}`] ?? titleMap[pathname] ?? "TechChoice Admin";

  return (
    <div className="admin-app flex min-h-screen">
      <AdminSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header title={title} onMenu={() => setSidebarOpen(true)} />
        <main className="flex-1 p-7"><div key={pathname} className="fade-up">{children}</div></main>
      </div>
    </div>
  );
}
