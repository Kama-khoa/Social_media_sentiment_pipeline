"use client";

import { useCallback, useEffect, useMemo, useState, type ComponentProps } from "react";
import { api } from "@/lib/api-client";
import type { ProductSpecTemplateItem } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";

const PAGE_SIZE = 10;
const valueTypes = [
  { value: "string", label: "string" },
  { value: "number", label: "number" },
  { value: "boolean", label: "boolean" },
];

function valueTypeVariant(value: string): ComponentProps<typeof Badge>["variant"] {
  if (value === "number") return "brand";
  if (value === "boolean") return "warning";
  return "secondary";
}

function categoryVariant(category: string): ComponentProps<typeof Badge>["variant"] {
  if (category.toLowerCase().includes("điện thoại") || category.toLowerCase().includes("phone")) return "brand";
  if (category.toLowerCase().includes("laptop")) return "success";
  if (category.toLowerCase().includes("tai nghe")) return "warning";
  return "secondary";
}

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

export default function ProductSpecTemplatesPage() {
  const [templates, setTemplates] = useState<ProductSpecTemplateItem[]>([]);
  const [filterCategory, setFilterCategory] = useState("all");
  const [page, setPage] = useState(1);
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    category: "",
    spec_key: "",
    display_label: "",
    value_type: "string" as "string" | "number" | "boolean",
    unit: "",
  });

  const categories = useMemo(
    () => Array.from(new Set(templates.map((item) => item.category))).sort((a, b) => a.localeCompare(b, "vi")),
    [templates],
  );
  const categoryOptions = useMemo(
    () => categories.map((category) => ({ value: category, label: category })),
    [categories],
  );
  const filteredTemplates = useMemo(
    () => filterCategory === "all" ? templates : templates.filter((item) => item.category === filterCategory),
    [filterCategory, templates],
  );
  const totalPages = pageCount(filteredTemplates.length);
  const visibleTemplates = filteredTemplates.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const nextTemplates = await api.admin.products.templates();
      setTemplates(nextTemplates);
      setError(null);
      setForm((current) => ({ ...current, category: current.category || nextTemplates[0]?.category || "" }));
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể tải mẫu thông số.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setPage(1); }, [filterCategory]);
  useEffect(() => { setPage((current) => Math.min(current, totalPages)); }, [totalPages]);

  async function createTemplate() {
    if (!form.category.trim() || !form.spec_key.trim() || !form.display_label.trim()) return;
    setSaving(true);
    try {
      await api.admin.products.createTemplate({
        category: form.category.trim(),
        spec_key: form.spec_key.trim(),
        display_label: form.display_label.trim(),
        value_type: form.value_type,
        unit: form.unit.trim() || undefined,
      });
      setForm({ category: form.category, spec_key: "", display_label: "", value_type: "string", unit: "" });
      setAddOpen(false);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể thêm mẫu thông số.");
    } finally {
      setSaving(false);
    }
  }

  async function deactivateTemplate(template: ProductSpecTemplateItem) {
    const confirmed = window.confirm("Tắt mẫu thông số này?");
    if (!confirmed) return;
    try {
      await api.admin.products.removeTemplate(template.category, template.spec_key);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể tắt mẫu thông số.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mẫu thông số kỹ thuật"
        description="Định nghĩa các trường specs chuẩn theo từng danh mục sản phẩm."
        action={<Button onClick={() => setAddOpen(true)}><Icon name="plus" size={16} />Thêm template</Button>}
      />

      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setFilterCategory("all")}
          className={`rounded-[10px] px-3.5 py-1.5 text-[13px] font-semibold shadow-[var(--shadow-sm)] transition-all ${filterCategory === "all" ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-none" : "bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
        >
          Tất cả ({templates.length})
        </button>
        {categories.map((category) => (
          <button
            key={category}
            onClick={() => setFilterCategory(category)}
            className={`rounded-[10px] px-3.5 py-1.5 text-[13px] font-semibold shadow-[var(--shadow-sm)] transition-all ${filterCategory === category ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-none" : "bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
          >
            {category} ({templates.filter((item) => item.category === category).length})
          </button>
        ))}
      </div>

      <Card className="overflow-hidden shadow-none">
        <div className="overflow-x-auto">
          <table className="tbl">
            <thead>
              <tr><th>Danh mục</th><th>spec_key</th><th>Nhãn hiển thị</th><th>Kiểu dữ liệu</th><th>Đơn vị</th><th>Trạng thái</th><th></th></tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, row) => (
                <tr key={row}>{Array.from({ length: 7 }).map((__, cell) => <td key={cell}><div className="h-4 animate-pulse rounded bg-[var(--surface-3)]" /></td>)}</tr>
              )) : visibleTemplates.length ? visibleTemplates.map((template) => (
                <tr key={`${template.category}-${template.spec_key}`}>
                  <td><Badge variant={categoryVariant(template.category)}>{template.category}</Badge></td>
                  <td><code className="num rounded-md bg-[var(--code-bg)] px-2 py-1 text-[12.5px] text-[var(--text-2)]">{template.spec_key}</code></td>
                  <td className="font-semibold">{template.display_label}</td>
                  <td><Badge variant={valueTypeVariant(template.value_type)}>{template.value_type}</Badge></td>
                  <td className="muted">{template.unit || "—"}</td>
                  <td>{template.is_active ? <Badge variant="success">Hoạt động</Badge> : <Badge>Đã tắt</Badge>}</td>
                  <td>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-[var(--neg)]"
                      disabled={!template.is_active}
                      onClick={() => void deactivateTemplate(template)}
                    >
                      <Icon name="trash" size={15} />
                    </Button>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={7} className="py-12 text-center text-sm text-[var(--text-3)]">Chưa có mẫu thông số phù hợp.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--text-3)]">
          <span>Trang {page}/{totalPages} · {filteredTemplates.length} mục</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Trước</Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>Sau</Button>
          </div>
        </div>
      </Card>

      <Modal open={addOpen} title="Thêm Spec Template" onClose={() => setAddOpen(false)}>
        <form onSubmit={(event) => { event.preventDefault(); void createTemplate(); }} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Danh mục *</label>
            <Dropdown value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} options={categoryOptions} placeholder="Chọn danh mục có sẵn" />
            <Input className="mt-2" value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))} placeholder="Hoặc nhập danh mục mới" />
          </div>
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">spec_key *</label>
            <Input value={form.spec_key} onChange={(event) => setForm((current) => ({ ...current, spec_key: event.target.value }))} placeholder="vd: screen_size, battery_capacity" />
          </div>
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Nhãn hiển thị *</label>
            <Input value={form.display_label} onChange={(event) => setForm((current) => ({ ...current, display_label: event.target.value }))} placeholder="vd: Màn hình, Dung lượng pin" />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Kiểu dữ liệu</label>
              <Dropdown value={form.value_type} onChange={(event) => setForm((current) => ({ ...current, value_type: event.target.value as "string" | "number" | "boolean" }))} options={valueTypes} />
            </div>
            <div>
              <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Đơn vị</label>
              <Input value={form.unit} onChange={(event) => setForm((current) => ({ ...current, unit: event.target.value }))} placeholder="GB, mAh, kg..." />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setAddOpen(false)}>Hủy</Button>
            <Button type="submit" disabled={saving || !form.category.trim() || !form.spec_key.trim() || !form.display_label.trim()}><Icon name="spec" size={16} />{saving ? "Đang thêm..." : "Thêm template"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
