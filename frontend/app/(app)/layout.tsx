"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  const titleMap: Record<string, string> = {
    "/dashboard": "Tổng quan",
    "/analytics/search": "Tìm kiếm sản phẩm",
    "/analytics/top-products": "Bảng xếp hạng",
    "/admin/channels": "Quản lý kênh YouTube",
    "/admin/keywords": "Quản lý từ khóa",
    "/admin/pipeline-health": "Vận hành Pipeline",
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar />
      <Header title={titleMap["/dashboard"] ?? "SentimentIQ"} />
      <main className="ml-56 pt-14 min-h-screen">
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
