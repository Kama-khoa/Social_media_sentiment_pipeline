"use client";

import { useCallback, useEffect, useMemo, useState, type ComponentProps } from "react";
import { api } from "@/lib/api-client";
import type { ProductAliasItem, ProductConfigItem } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";

const PAGE_SIZE = 10;
const aliasTypes = [
  { value: "common_name", label: "Tên thường gọi" },
  { value: "variant", label: "Biến thể" },
  { value: "abbreviation", label: "Viết tắt" },
  { value: "typo", label: "Lỗi chính tả" },
  { value: "exact", label: "Chính xác" },
];

function aliasTypeLabel(value: string) {
  return aliasTypes.find((item) => item.value === value)?.label ?? value;
}

function aliasTypeVariant(value: string): ComponentProps<typeof Badge>["variant"] {
  if (value === "abbreviation") return "brand";
  if (value === "typo") return "destructive";
  if (value === "exact") return "success";
  return "secondary";
}

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

export default function ProductAliasesPage() {
  const [aliases, setAliases] = useState<ProductAliasItem[]>([]);
  const [products, setProducts] = useState<ProductConfigItem[]>([]);
  const [filterProductId, setFilterProductId] = useState("all");
  const [page, setPage] = useState(1);
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ product_id: "", alias_text: "", alias_type: "common_name" });

  const productNameById = useMemo(
    () => new Map(products.map((item) => [item.product_id, item.product_name])),
    [products],
  );
  const productOptions = useMemo(
    () => products.map((item) => ({ value: item.product_id, label: item.product_name })),
    [products],
  );
  const filteredAliases = useMemo(
    () => filterProductId === "all" ? aliases : aliases.filter((item) => item.product_id === filterProductId),
    [aliases, filterProductId],
  );
  const totalPages = pageCount(filteredAliases.length);
  const visibleAliases = filteredAliases.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const productsWithAliases = useMemo(
    () => products
      .map((product) => ({ product, count: aliases.filter((alias) => alias.product_id === product.product_id).length }))
      .filter((item) => item.count > 0),
    [aliases, products],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextAliases, nextProducts] = await Promise.all([
        api.admin.products.aliases(),
        api.admin.products.list(),
      ]);
      setAliases(nextAliases);
      setProducts(nextProducts);
      setError(null);
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể tải danh sách alias.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setPage(1); }, [filterProductId]);
  useEffect(() => { setPage((current) => Math.min(current, totalPages)); }, [totalPages]);

  async function createAlias() {
    if (!form.product_id || !form.alias_text.trim()) return;
    setSaving(true);
    try {
      await api.admin.products.createAlias({
        product_id: form.product_id,
        alias_text: form.alias_text.trim(),
        alias_type: form.alias_type,
      });
      setForm({ product_id: "", alias_text: "", alias_type: "common_name" });
      setAddOpen(false);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể thêm alias.");
    } finally {
      setSaving(false);
    }
  }

  async function deactivateAlias(aliasId: string) {
    const confirmed = window.confirm("Tắt alias này?");
    if (!confirmed) return;
    try {
      await api.admin.products.removeAlias(aliasId);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể tắt alias.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Tên gọi khác (Alias)"
        description={`${aliases.length} tên gọi khác đang quản lý để khớp sản phẩm từ bình luận YouTube.`}
        action={<Button onClick={() => setAddOpen(true)}><Icon name="plus" size={16} />Thêm alias</Button>}
      />

      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setFilterProductId("all")}
          className={`rounded-[10px] px-3.5 py-1.5 text-[13px] font-semibold shadow-[var(--shadow-sm)] transition-all ${filterProductId === "all" ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-none" : "bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
        >
          Tất cả ({aliases.length})
        </button>
        {productsWithAliases.map(({ product, count }) => (
          <button
            key={product.product_id}
            onClick={() => setFilterProductId(product.product_id)}
            className={`rounded-[10px] px-3.5 py-1.5 text-[13px] font-semibold shadow-[var(--shadow-sm)] transition-all ${filterProductId === product.product_id ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-none" : "bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
          >
            {product.product_name} ({count})
          </button>
        ))}
      </div>

      <Card className="overflow-hidden shadow-none">
        <div className="overflow-x-auto">
          <table className="tbl">
            <thead>
              <tr><th>Alias text</th><th>Sản phẩm</th><th>Loại</th><th>Trạng thái</th><th>Ngày tạo</th><th></th></tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, row) => (
                <tr key={row}>{Array.from({ length: 6 }).map((__, cell) => <td key={cell}><div className="h-4 animate-pulse rounded bg-[var(--surface-3)]" /></td>)}</tr>
              )) : visibleAliases.length ? visibleAliases.map((alias) => (
                <tr key={alias.alias_id}>
                  <td>
                    <code className="num rounded-md bg-[var(--code-bg)] px-2.5 py-1 text-[13px] font-bold text-[var(--primary)]">{alias.alias_text}</code>
                  </td>
                  <td className="font-semibold">{productNameById.get(alias.product_id) ?? alias.product_id}</td>
                  <td><Badge variant={aliasTypeVariant(alias.alias_type)}>{aliasTypeLabel(alias.alias_type)}</Badge></td>
                  <td>{alias.is_active ? <Badge variant="success">Hoạt động</Badge> : <Badge>Đã tắt</Badge>}</td>
                  <td className="num muted text-[13px]">{new Date(alias.created_at).toLocaleDateString("vi-VN")}</td>
                  <td>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-[var(--neg)]"
                      disabled={!alias.is_active}
                      onClick={() => void deactivateAlias(alias.alias_id)}
                    >
                      <Icon name="trash" size={15} />
                    </Button>
                  </td>
                </tr>
              )) : (
                <tr><td colSpan={6} className="py-12 text-center text-sm text-[var(--text-3)]">Chưa có alias phù hợp.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--text-3)]">
          <span>Trang {page}/{totalPages} · {filteredAliases.length} mục</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Trước</Button>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>Sau</Button>
          </div>
        </div>
      </Card>

      <Modal open={addOpen} title="Thêm alias mới" onClose={() => setAddOpen(false)}>
        <form onSubmit={(event) => { event.preventDefault(); void createAlias(); }} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Alias text *</label>
            <Input value={form.alias_text} onChange={(event) => setForm((current) => ({ ...current, alias_text: event.target.value }))} placeholder="vd: ip17pm, s25 ultra 5g..." />
          </div>
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Sản phẩm *</label>
            <Dropdown value={form.product_id} onChange={(event) => setForm((current) => ({ ...current, product_id: event.target.value }))} options={productOptions} placeholder="Chọn sản phẩm" />
          </div>
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Loại alias</label>
            <Dropdown value={form.alias_type} onChange={(event) => setForm((current) => ({ ...current, alias_type: event.target.value }))} options={aliasTypes} />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setAddOpen(false)}>Hủy</Button>
            <Button type="submit" disabled={saving || !form.product_id || !form.alias_text.trim()}><Icon name="link" size={16} />{saving ? "Đang thêm..." : "Thêm alias"}</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
