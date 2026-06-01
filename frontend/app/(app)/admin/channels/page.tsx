"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { api } from "@/lib/api-client";
import type { ChannelConfigItem } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";

type ChannelForm = {
  channel_id: string;
  channel_name: string;
  channel_url: string;
  channel_handle: string;
  subscriber_count: string;
};

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
      active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
    }`}>
      {active ? "Đang hoạt động" : "Đã tắt"}
    </span>
  );
}

function HistoricalBadge({ scanned }: { scanned: boolean }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
      scanned ? "bg-blue-100 text-blue-700" : "bg-amber-100 text-amber-700"
    }`}>
      {scanned ? "Đã scan" : "Chưa scan"}
    </span>
  );
}

export default function ChannelsPage() {
  const [channels, setChannels] = useState<ChannelConfigItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [mode, setMode] = useState<"add" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<ChannelConfigItem | null>(null);
  const [confirmDeactivateId, setConfirmDeactivateId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ChannelForm>({
    defaultValues: { channel_id: "", channel_name: "", channel_url: "", channel_handle: "", subscriber_count: "" },
  });

  async function load() {
    setLoading(true);
    setPageError(null);
    try {
      setChannels(await api.admin.channels.list());
    } catch {
      setPageError("Không thể tải danh sách kênh. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function openAdd() {
    reset({ channel_id: "", channel_name: "", channel_url: "", channel_handle: "", subscriber_count: "" });
    setEditTarget(null);
    setFormError(null);
    setMode("add");
  }

  function openEdit(ch: ChannelConfigItem) {
    reset({
      channel_id: ch.channel_id,
      channel_name: ch.channel_name,
      channel_url: ch.channel_url ?? "",
      channel_handle: ch.channel_handle ?? "",
      subscriber_count: ch.subscriber_count?.toString() ?? "",
    });
    setEditTarget(ch);
    setFormError(null);
    setMode("edit");
  }

  async function onSubmit(data: ChannelForm) {
    setSaving(true);
    setFormError(null);
    try {
      const payload = {
        channel_name: data.channel_name.trim(),
        channel_url: data.channel_url.trim() || undefined,
        channel_handle: data.channel_handle.trim() || undefined,
        subscriber_count: data.subscriber_count ? parseInt(data.subscriber_count, 10) : undefined,
      };
      if (mode === "add") {
        await api.admin.channels.create({ channel_id: data.channel_id.trim(), ...payload });
      } else if (editTarget) {
        await api.admin.channels.update(editTarget.channel_id, payload);
      }
      setMode(null);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setFormError(e?.detail ?? "Không thể lưu thay đổi.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate() {
    if (!confirmDeactivateId) return;
    try {
      await api.admin.channels.remove(confirmDeactivateId);
      setConfirmDeactivateId(null);
      await load();
    } catch {
      setPageError("Không thể tắt kênh. Vui lòng thử lại.");
      setConfirmDeactivateId(null);
    }
  }

  const activeCount = channels.filter((c) => c.is_active).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Quản lý kênh YouTube</h1>
          <p className="text-sm text-slate-500 mt-0.5">Kênh dùng để thu thập video và bình luận cho pipeline</p>
        </div>
        <button
          onClick={openAdd}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm kênh
        </button>
      </div>

      {pageError && (
        <div className="mb-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg px-4 py-3">
          {pageError}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Kênh</th>
              <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Handle</th>
              <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Trạng thái</th>
              <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Historical</th>
              <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Ngày thêm</th>
              <th className="px-4 py-3 text-right text-xs text-slate-500 font-medium uppercase tracking-wider">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-slate-100">
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-4">
                      <div className="h-4 bg-slate-100 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : channels.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-slate-400 text-sm">
                  Chưa có kênh nào. Nhấn "Thêm kênh" để bắt đầu.
                </td>
              </tr>
            ) : (
              channels.map((ch) => (
                <tr
                  key={ch.channel_id}
                  className={`border-b border-slate-100 hover:bg-slate-50/50 transition-colors ${!ch.is_active ? "opacity-60" : ""}`}
                >
                  <td className="px-4 py-3.5">
                    <div className="font-medium text-slate-800">{ch.channel_name}</div>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">{ch.channel_id}</div>
                  </td>
                  <td className="px-4 py-3.5 text-slate-500 text-xs">{ch.channel_handle ?? "—"}</td>
                  <td className="px-4 py-3.5"><StatusBadge active={ch.is_active} /></td>
                  <td className="px-4 py-3.5"><HistoricalBadge scanned={ch.is_historically_scanned} /></td>
                  <td className="px-4 py-3.5 text-xs text-slate-400">
                    {new Date(ch.created_at).toLocaleDateString("vi-VN")}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center justify-end gap-3">
                      <button
                        onClick={() => openEdit(ch)}
                        className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
                      >
                        Sửa
                      </button>
                      {ch.is_active && (
                        <button
                          onClick={() => setConfirmDeactivateId(ch.channel_id)}
                          className="text-xs text-rose-500 hover:text-rose-700 font-medium transition-colors"
                        >
                          Tắt
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {!loading && channels.length > 0 && (
          <div className="px-4 py-3 border-t border-slate-100 text-xs text-slate-400">
            {activeCount} kênh đang hoạt động · {channels.length} tổng cộng
          </div>
        )}
      </div>

      {/* Add / Edit dialog */}
      <Modal
        open={mode !== null}
        title={mode === "add" ? "Thêm kênh YouTube" : "Sửa thông tin kênh"}
        onClose={() => setMode(null)}
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {formError && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg px-3 py-2">
              {formError}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Channel ID <span className="text-rose-500">*</span>
            </label>
            <input
              {...register("channel_id", { required: "Bắt buộc" })}
              disabled={mode === "edit"}
              placeholder="UCxxxxxxxxxxxxxxxxxxxxxxxx"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 disabled:bg-slate-50 disabled:text-slate-400"
            />
            {errors.channel_id && <p className="text-xs text-rose-500 mt-1">{errors.channel_id.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Tên kênh <span className="text-rose-500">*</span>
            </label>
            <input
              {...register("channel_name", { required: "Bắt buộc" })}
              placeholder="Tên hiển thị của kênh"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
            />
            {errors.channel_name && <p className="text-xs text-rose-500 mt-1">{errors.channel_name.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">URL kênh</label>
            <input
              {...register("channel_url")}
              placeholder="https://youtube.com/channel/..."
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Handle</label>
            <input
              {...register("channel_handle")}
              placeholder="@channelname"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Số người đăng ký</label>
            <input
              {...register("subscriber_count", {
                pattern: { value: /^\d*$/, message: "Phải là số nguyên dương" },
              })}
              placeholder="1000000"
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
            />
            {errors.subscriber_count && <p className="text-xs text-rose-500 mt-1">{errors.subscriber_count.message}</p>}
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setMode(null)}
              className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {saving ? "Đang lưu…" : mode === "add" ? "Thêm kênh" : "Lưu thay đổi"}
            </button>
          </div>
        </form>
      </Modal>

      {/* Confirm deactivate dialog */}
      <Modal
        open={confirmDeactivateId !== null}
        title="Xác nhận tắt kênh"
        onClose={() => setConfirmDeactivateId(null)}
      >
        <div className="space-y-5">
          <p className="text-sm text-slate-600">
            Kênh sẽ được đặt thành <strong className="text-slate-800">không hoạt động</strong>. Pipeline sẽ không thu thập video từ kênh này cho đến khi được kích hoạt lại.
          </p>
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setConfirmDeactivateId(null)}
              className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Hủy
            </button>
            <button
              onClick={handleDeactivate}
              className="px-4 py-2 text-sm bg-rose-600 hover:bg-rose-700 text-white font-medium rounded-lg transition-colors"
            >
              Tắt kênh
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
