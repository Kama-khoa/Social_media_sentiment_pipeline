"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "", display_name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.auth.register(form.email, form.password, form.display_name);
      router.push("/login");
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Đăng ký thất bại");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell fade-in flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 mb-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[var(--v-500)] to-[var(--v-700)] text-white shadow-[0_6px_14px_-4px_var(--ring)]">
              ✦
            </div>
          </div>
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">Tạo tài khoản TechChoice</h1>
          <p className="text-slate-500 mt-2 text-sm">Bắt đầu phân tích sản phẩm công nghệ</p>
        </div>

        <Card className="p-6 shadow-[var(--shadow-lg)] sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Tên hiển thị</label>
              <Input
                type="text"
                value={form.display_name}
                onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
                placeholder="Nguyễn Văn A"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="you@example.com"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Mật khẩu</label>
              <Input
                type="password"
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                placeholder="Tối thiểu 8 ký tự"
                required
                minLength={8}
              />
            </div>

            {error && (
              <div className="rounded-lg bg-rose-50 border border-rose-200 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="mt-2 w-full"
            >
              {loading ? "Đang tạo tài khoản..." : "Tạo tài khoản an toàn"}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-100 text-center">
            <p className="text-sm text-slate-500">
              Đã có tài khoản?{" "}
              <Link href="/login" className="text-indigo-600 hover:text-indigo-700 font-medium">
                Đăng nhập ngay
              </Link>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
