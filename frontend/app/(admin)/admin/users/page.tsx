"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { api } from "@/lib/api-client";
import type { AdminUserItem } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { PageHeader } from "@/components/shared/PageHeader";
import { Switch } from "@/components/ui/switch";

type UserForm = {
  email: string;
  display_name: string;
  password: string;
  role: "user" | "admin";
};

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [mode, setMode] = useState<"create" | "edit" | null>(null);
  const [target, setTarget] = useState<AdminUserItem | null>(null);
  const [saving, setSaving] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<UserForm>({
    defaultValues: { email: "", display_name: "", password: "", role: "user" },
  });

  async function load() {
    setLoading(true);
    setPageError(null);
    try {
      setUsers(await api.admin.users.list());
    } catch {
      setPageError("Không thể tải danh sách tài khoản.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function openCreate() {
    setTarget(null);
    setFormError(null);
    reset({ email: "", display_name: "", password: "", role: "user" });
    setMode("create");
  }

  function openEdit(user: AdminUserItem) {
    setTarget(user);
    setFormError(null);
    reset({ email: user.email, display_name: user.display_name, password: "", role: user.role });
    setMode("edit");
  }

  async function onSubmit(data: UserForm) {
    setSaving(true);
    setFormError(null);
    try {
      if (mode === "create") {
        await api.admin.users.create({
          email: data.email.trim(),
          display_name: data.display_name.trim(),
          password: data.password,
          role: data.role,
        });
      } else if (target) {
        await api.admin.users.update(target.id, {
          display_name: data.display_name.trim(),
          role: data.role,
          ...(data.password ? { password: data.password } : {}),
        });
      }
      setMode(null);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setFormError(e?.detail ?? "Không thể lưu tài khoản.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(user: AdminUserItem) {
    setPageError(null);
    try {
      await api.admin.users.update(user.id, { is_active: !user.is_active });
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setPageError(e?.detail ?? "Không thể cập nhật trạng thái tài khoản.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản lý tài khoản"
        description="Tài khoản đăng nhập dashboard và phân quyền quản trị."
        action={<Button onClick={openCreate}>Thêm tài khoản</Button>}
      />

      {pageError && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{pageError}</div>}

      <Card className="overflow-hidden shadow-none">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Tài khoản</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Vai trò</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Trạng thái</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500">Đăng nhập cuối</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-slate-500">Hành động</th>
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, index) => (
                <tr key={index} className="border-b border-slate-100">
                  {Array.from({ length: 5 }).map((__, cell) => <td key={cell} className="px-4 py-4"><div className="h-4 animate-pulse rounded bg-slate-100" /></td>)}
                </tr>
              )) : users.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-12 text-center text-sm text-slate-400">Chưa có tài khoản nào.</td></tr>
              ) : users.map((user) => (
                <tr key={user.id} className={`border-b border-slate-100 transition-colors hover:bg-slate-50/50 ${!user.is_active ? "opacity-60" : ""}`}>
                  <td className="px-4 py-3.5">
                    <div className="font-semibold text-slate-800">{user.display_name}</div>
                    <div className="mt-1 text-xs text-slate-400">{user.email}</div>
                  </td>
                  <td className="px-4 py-3.5"><Badge variant={user.role === "admin" ? "brand" : "secondary"}>{user.role === "admin" ? "Quản trị viên" : "Người dùng"}</Badge></td>
                  <td className="px-4 py-3.5"><div className="flex items-center gap-2"><Switch checked={user.is_active} onClick={() => toggleActive(user)} label={`Bật hoặc tắt ${user.email}`} /><span className="text-xs text-slate-500">{user.is_active ? "Đang hoạt động" : "Đã tắt"}</span></div></td>
                  <td className="px-4 py-3.5 text-xs text-slate-400">{user.last_login_at ? new Date(user.last_login_at).toLocaleString("vi-VN") : "Chưa đăng nhập"}</td>
                  <td className="px-4 py-3.5 text-right"><Button onClick={() => openEdit(user)} variant="ghost" size="sm" className="text-indigo-600">Sửa</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={mode !== null} title={mode === "create" ? "Thêm tài khoản" : "Sửa tài khoản"} onClose={() => setMode(null)}>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {formError && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{formError}</div>}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
            <Input {...register("email", { required: "Bắt buộc" })} type="email" disabled={mode === "edit"} />
            {errors.email && <p className="mt-1 text-xs text-rose-500">{errors.email.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Tên hiển thị</label>
            <Input {...register("display_name", { required: "Bắt buộc", minLength: { value: 2, message: "Ít nhất 2 ký tự" } })} />
            {errors.display_name && <p className="mt-1 text-xs text-rose-500">{errors.display_name.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{mode === "create" ? "Mật khẩu" : "Mật khẩu mới"}</label>
            <Input {...register("password", mode === "create" ? { required: "Bắt buộc", minLength: { value: 8, message: "Ít nhất 8 ký tự" } } : { minLength: { value: 8, message: "Ít nhất 8 ký tự" } })} type="password" placeholder={mode === "edit" ? "Để trống nếu không đổi" : ""} />
            {errors.password && <p className="mt-1 text-xs text-rose-500">{errors.password.message}</p>}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Vai trò</label>
            <Select {...register("role")}><option value="user">Người dùng</option><option value="admin">Quản trị viên</option></Select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" onClick={() => setMode(null)} variant="outline">Hủy</Button>
            <Button type="submit" disabled={saving}>{saving ? "Đang lưu..." : "Lưu tài khoản"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
