"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { api } from "@/lib/api-client";
import type { KeywordConfigItem } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CustomSelect } from "@/components/ui/custom-select";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Switch } from "@/components/ui/switch";

type KeywordForm = {
  keyword_text: string;
  search_cluster: string;
};

export default function KeywordsPage() {
  const [keywords, setKeywords] = useState<KeywordConfigItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCluster, setFilterCluster] = useState("all");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;
  const [pageError, setPageError] = useState<string | null>(null);
  const [mode, setMode] = useState<"add" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<KeywordConfigItem | null>(null);
  const [confirmDeactivateId, setConfirmDeactivateId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const { register, handleSubmit, reset, formState: { errors } } = useForm<KeywordForm>({
    defaultValues: { keyword_text: "", search_cluster: "" },
  });

  async function load() {
    setLoading(true);
    setPageError(null);
    try {
      setKeywords(await api.admin.keywords.list());
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setPageError(e?.detail ?? "Không thể tải danh sách từ khóa. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function openAdd() {
    reset({ keyword_text: "", search_cluster: "" });
    setEditTarget(null);
    setFormError(null);
    setMode("add");
  }

  function openEdit(kw: KeywordConfigItem) {
    reset({ keyword_text: kw.keyword_text, search_cluster: kw.search_cluster ?? "" });
    setEditTarget(kw);
    setFormError(null);
    setMode("edit");
  }

  async function onSubmit(data: KeywordForm) {
    setSaving(true);
    setFormError(null);
    try {
      const payload = {
        keyword_text: data.keyword_text.trim(),
        search_cluster: data.search_cluster.trim() || undefined,
      };
      if (mode === "add") {
        await api.admin.keywords.create(payload);
      } else if (editTarget) {
        await api.admin.keywords.update(editTarget.keyword_id, payload);
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
      await api.admin.keywords.remove(confirmDeactivateId);
      setConfirmDeactivateId(null);
      await load();
    } catch {
      setPageError("Không thể tắt từ khóa. Vui lòng thử lại.");
      setConfirmDeactivateId(null);
    }
  }

  const activeCount = keywords.filter((k) => k.is_active).length;

  const clusters = Array.from(new Set(keywords.map((k) => k.search_cluster).filter(Boolean))) as string[];
  const clusterOptions = [
    { value: "all", label: "Tất cả nhóm" },
    ...clusters.map(c => ({ value: c, label: c }))
  ];

  const filteredKeywords = keywords.filter((kw) => {
    const matchSearch = kw.keyword_text.toLowerCase().includes(searchQuery.toLowerCase());
    const matchCluster = filterCluster === "all" || kw.search_cluster === filterCluster;
    return matchSearch && matchCluster;
  });

  const pageCount = Math.max(1, Math.ceil(filteredKeywords.length / PAGE_SIZE));
  const paginatedKeywords = filteredKeywords.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Reset page if filtered results are fewer than current page allows
  useEffect(() => {
    if (page > pageCount) setPage(1);
  }, [filteredKeywords.length, page, pageCount]);

  return (
    <div>
      <div className="mb-6">
        <PageHeader
          title="Quản lý từ khóa tìm kiếm"
          description="Các từ khóa tìm kiếm dùng để khám phá video liên quan trên YouTube."
        />
      </div>

      {pageError && (
        <div className="mb-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg px-4 py-3">
          {pageError}
        </div>
      )}

      <Card className="p-4 mb-4 flex gap-3 flex-wrap shadow-none border-slate-200 bg-white items-center">
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Nhập từ khóa cần tìm..."
          className="flex-1 min-w-[200px]"
        />
        <div className="w-full sm:w-[240px] z-10">
          <CustomSelect
            value={filterCluster}
            onChange={setFilterCluster}
            options={clusterOptions}
            className="w-full [&>button]:!min-w-0 [&>button]:!w-full [&>button]:!h-10 [&>button]:!rounded-md [&>button]:!text-sm [&>button]:!font-normal [&>button]:!shadow-none [&>button]:!border-slate-200 hover:[&>button]:!border-slate-300"
          />
        </div>
        <Button onClick={openAdd} className="bg-indigo-600 hover:bg-indigo-700">
          <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Thêm từ khóa
        </Button>
      </Card>

      <Card className="overflow-hidden shadow-none">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Từ khóa</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Nhóm</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Trạng thái</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Ngày thêm</th>
                <th className="px-4 py-3 text-right text-xs text-slate-500 font-medium uppercase tracking-wider">Hành động</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <td key={j} className="px-4 py-4">
                        <div className="h-4 bg-slate-100 rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : filteredKeywords.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-slate-400 text-sm">
                    {searchQuery || filterCluster !== "all" 
                      ? "Không tìm thấy từ khóa nào phù hợp." 
                      : "Chưa có từ khóa nào. Nhấn \"Thêm từ khóa\" để bắt đầu."}
                  </td>
                </tr>
              ) : (
                paginatedKeywords.map((kw) => (
                  <tr
                    key={kw.keyword_id}
                    className={`border-b border-slate-100 hover:bg-slate-50/50 transition-colors ${!kw.is_active ? "opacity-60" : ""}`}
                  >
                    <td className="px-4 py-3.5">
                      <span className="font-medium font-mono text-slate-800">{kw.keyword_text}</span>
                    </td>
                    <td className="px-4 py-3.5">
                      {kw.search_cluster ? (
                        <Badge variant="brand" className="bg-slate-100 text-slate-700 hover:bg-slate-200">{kw.search_cluster}</Badge>
                      ) : (
                        <span className="text-slate-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <Switch checked={kw.is_active} onClick={kw.is_active ? () => setConfirmDeactivateId(kw.keyword_id) : undefined} disabled={!kw.is_active} label={`Bật hoặc tắt ${kw.keyword_text}`} />
                        <StatusBadge active={kw.is_active} />
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400">
                      {new Date(kw.created_at).toLocaleDateString("vi-VN")}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEdit(kw)}
                          className="h-8 w-8 rounded-lg flex items-center justify-center text-slate-500 hover:bg-slate-100 hover:text-indigo-600 transition-colors"
                          title="Sửa"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        {kw.is_active && (
                          <button
                            onClick={() => setConfirmDeactivateId(kw.keyword_id)}
                            className="h-8 w-8 rounded-lg flex items-center justify-center text-slate-500 hover:bg-slate-100 hover:text-rose-500 transition-colors"
                            title="Tắt"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {!loading && filteredKeywords.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-xs text-[var(--text-3)]">
            <span>
              {activeCount} từ khóa đang hoạt động · {filteredKeywords.length} tổng cộng · Hiển thị {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, filteredKeywords.length)}
            </span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Trước</Button>
              <span className="num text-[var(--text-2)] font-medium text-slate-500">Trang {page}/{pageCount}</span>
              <Button variant="outline" size="sm" disabled={page >= pageCount} onClick={() => setPage((current) => Math.min(pageCount, current + 1))}>Sau</Button>
            </div>
          </div>
        )}
      </Card>

      {/* Add / Edit dialog */}
      <Modal
        open={mode !== null}
        title={mode === "add" ? "Thêm từ khóa" : "Sửa từ khóa"}
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
              Từ khóa <span className="text-rose-500">*</span>
            </label>
            <Input
              {...register("keyword_text", { required: "Bắt buộc" })}
              placeholder="vd: Samsung Galaxy S25, iPhone 16..."
            />
            {errors.keyword_text && <p className="text-xs text-rose-500 mt-1">{errors.keyword_text.message}</p>}
            <p className="text-xs text-slate-400 mt-1">Từ khóa phân biệt hoa thường khi tìm kiếm trên YouTube</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Nhóm (search_cluster)</label>
            <Input
              {...register("search_cluster")}
              placeholder="vd: Điện thoại, Laptop, Tai nghe..."
              list="cluster-suggestions"
            />
            {clusters.length > 0 && (
              <datalist id="cluster-suggestions">
                {clusters.map((c) => <option key={c} value={c} />)}
              </datalist>
            )}
            <p className="text-xs text-slate-400 mt-1">Dùng để nhóm các từ khóa liên quan lại với nhau</p>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              onClick={() => setMode(null)}
              variant="outline"
            >
              Hủy
            </Button>
            <Button
              type="submit"
              disabled={saving}
            >
              {saving ? "Đang lưu…" : mode === "add" ? "Thêm từ khóa" : "Lưu thay đổi"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Confirm deactivate dialog */}
      <Modal
        open={confirmDeactivateId !== null}
        title="Xác nhận tắt từ khóa"
        onClose={() => setConfirmDeactivateId(null)}
      >
        <div className="space-y-5">
          <p className="text-sm text-slate-600">
            Từ khóa sẽ không còn được dùng trong lần thu thập video tiếp theo. Hành động này có thể hoàn tác bằng cách kích hoạt lại qua BigQuery Console.
          </p>
          <div className="flex justify-end gap-3">
            <Button
              onClick={() => setConfirmDeactivateId(null)}
              variant="outline"
            >
              Hủy
            </Button>
            <Button
              onClick={handleDeactivate}
              variant="destructive"
            >
              Tắt từ khóa
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
