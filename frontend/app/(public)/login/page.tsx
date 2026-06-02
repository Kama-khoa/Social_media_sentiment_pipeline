"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const me = await login(email, password);
      if (me.role === "admin") {
        router.push("/admin");
      } else {
        router.push("/");
      }
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Đăng nhập thất bại");
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
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">Đăng nhập TechChoice</h1>
          <p className="text-slate-500 mt-2 text-sm">Nền tảng phân tích cảm xúc đánh giá công nghệ</p>
        </div>

        <Card className="p-6 shadow-[var(--shadow-lg)] sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Email</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Mật khẩu</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
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
              {loading ? "Đang đăng nhập..." : "Đăng nhập an toàn"}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-100 text-center">
            <p className="text-sm text-slate-500">
              Chưa có tài khoản?{" "}
              <Link href="/register" className="text-indigo-600 hover:text-indigo-700 font-medium">
                Đăng ký ngay
              </Link>
            </p>
          </div>

        </Card>
      </div>
    </div>
  );
}
