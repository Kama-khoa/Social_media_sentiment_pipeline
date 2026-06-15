"use client";

import { useCallback, useEffect, useMemo, useState, type ComponentProps } from "react";
import { api } from "@/lib/api-client";
import type { ProductConfigItem, ProductDetailChangeRequestItem } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";

const PAGE_SIZE = 10;
const requestStatuses = [
  { value: "pending", label: "Đang chờ", variant: "warning" },
  { value: "approved", label: "Đã duyệt", variant: "success" },
  { value: "rejected", label: "Từ chối", variant: "destructive" },
] as const;

type ProductForm = {
  product_id: string;
  product_name: string;
  brand: string;
  category: string;
  release_year: string;
};

const emptyProductForm: ProductForm = {
  product_id: "",
  product_name: "",
  brand: "",
  category: "",
  release_year: "",
};

function pageCount(total: number) {
  return Math.max(1, Math.ceil(total / PAGE_SIZE));
}

function statusVariant(value: string): ComponentProps<typeof Badge>["variant"] {
  return requestStatuses.find((item) => item.value === value)?.variant ?? "secondary";
}

function statusLabel(value: string) {
  return requestStatuses.find((item) => item.value === value)?.label ?? value;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("vi-VN");
}

export default function ProductsAdminPage() {
  const [tab, setTab] = useState<"catalog" | "requests">("catalog");
  const [products, setProducts] = useState<ProductConfigItem[]>([]);
  const [requests, setRequests] = useState<Record<string, ProductDetailChangeRequestItem[]>>({ pending: [], approved: [], rejected: [] });
  const [categoryFilter, setCategoryFilter] = useState("");
  const [page, setPage] = useState(1);
  const [productModalOpen, setProductModalOpen] = useState(false);
  const [requestModal, setRequestModal] = useState<ProductDetailChangeRequestItem | null>(null);
  const [savingProduct, setSavingProduct] = useState(false);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [productForm, setProductForm] = useState<ProductForm>(emptyProductForm);

  const categories = useMemo(
    () => Array.from(new Set(products.map((item) => item.category).filter(Boolean) as string[])).sort((a, b) => a.localeCompare(b, "vi")),
    [products],
  );
  const categoryOptions = useMemo(
    () => categories.map((category) => ({ value: category, label: category })),
    [categories],
  );
  const filteredProducts = useMemo(
    () => categoryFilter ? products.filter((item) => item.category === categoryFilter) : products,
    [categoryFilter, products],
  );
  const totalPages = pageCount(filteredProducts.length);
  const visibleProducts = filteredProducts.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const pendingRequestCount = requests.pending?.length ?? 0;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextProducts, pending, approved, rejected] = await Promise.all([
        api.admin.products.list(),
        api.admin.products.detailRequests("pending"),
        api.admin.products.detailRequests("approved"),
        api.admin.products.detailRequests("rejected"),
      ]);
      setProducts(nextProducts);
      setRequests({ pending, approved, rejected });
      setError(null);
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể tải catalog sản phẩm.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setPage(1); }, [categoryFilter]);
  useEffect(() => { setPage((current) => Math.min(current, totalPages)); }, [totalPages]);

  async function createProduct() {
    if (!productForm.product_name.trim()) return;
    setSavingProduct(true);
    try {
      await api.admin.products.create({
        product_id: productForm.product_id.trim() || undefined,
        product_name: productForm.product_name.trim(),
        brand: productForm.brand.trim() || undefined,
        category: productForm.category.trim() || undefined,
        release_year: productForm.release_year ? Number(productForm.release_year) : undefined,
      });
      setProductForm(emptyProductForm);
      setProductModalOpen(false);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể thêm sản phẩm.");
    } finally {
      setSavingProduct(false);
    }
  }

  async function reviewRequest(requestId: string, action: "approve" | "reject") {
    setReviewingId(requestId);
    try {
      await api.admin.products.reviewDetailRequest(requestId, action);
      setRequestModal(null);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể xử lý phiếu chỉnh sửa.");
    } finally {
      setReviewingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản lý sản phẩm"
        description="Catalog sản phẩm và phiếu đề xuất chỉnh sửa thông tin từ người dùng."
        action={<Button onClick={() => setProductModalOpen(true)}><Icon name="plus" size={16} />Thêm sản phẩm</Button>}
      />

      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => setTab("catalog")}
          className={`rounded-[10px] px-4 py-2 text-[13.5px] font-semibold shadow-[var(--shadow-sm)] transition-all ${tab === "catalog" ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-none" : "bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
        >
          Danh mục sản phẩm
        </button>
        <button
          onClick={() => setTab("requests")}
          className={`rounded-[10px] px-4 py-2 text-[13.5px] font-semibold shadow-[var(--shadow-sm)] transition-all ${tab === "requests" ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-none" : "bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
        >
          Phiếu chỉnh sửa <span className="ml-2 opacity-70">{pendingRequestCount}</span>
        </button>
      </div>

      {tab === "catalog" ? (
        <Card className="overflow-hidden shadow-none">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
            <div>
              <h2 className="font-bold text-[var(--text)]">Sản phẩm ({filteredProducts.length})</h2>
              <p className="mt-1 text-xs text-[var(--text-3)]">10 bản ghi/trang · dữ liệu từ product_config.</p>
            </div>
            <Dropdown value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} options={categoryOptions} placeholder="Tất cả danh mục" className="w-48" />
          </div>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Sản phẩm</th><th>Thương hiệu</th><th>Danh mục</th><th>Năm</th><th>ID</th><th>Trạng thái</th></tr></thead>
              <tbody>
                {loading ? Array.from({ length: PAGE_SIZE }).map((_, row) => (
                  <tr key={row}>{Array.from({ length: 6 }).map((__, cell) => <td key={cell}><div className="h-4 animate-pulse rounded bg-[var(--surface-3)]" /></td>)}</tr>
                )) : visibleProducts.length ? visibleProducts.map((item) => (
                  <tr key={item.product_id}>
                    <td className="font-bold">{item.product_name}</td>
                    <td className="muted">{item.brand ?? "—"}</td>
                    <td>{item.category ? <Badge>{item.category}</Badge> : <span className="muted">—</span>}</td>
                    <td className="num muted">{item.release_year ?? "—"}</td>
                    <td><code className="num rounded-md bg-[var(--code-bg)] px-2 py-1 text-xs text-[var(--text-2)]">{item.product_id}</code></td>
                    <td>{item.is_active ? <Badge variant="success">Đang hiển thị</Badge> : <Badge>Đã tắt</Badge>}</td>
                  </tr>
                )) : (
                  <tr><td colSpan={6} className="py-12 text-center text-sm text-[var(--text-3)]">Không có sản phẩm phù hợp.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--text-3)]">
            <span>Trang {page}/{totalPages}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Trước</Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>Sau</Button>
            </div>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          {requestStatuses.map((status) => {
            const rows = requests[status.value] ?? [];
            return (
              <section key={status.value} className="rounded-[14px] border-2 border-dashed border-transparent bg-[var(--surface-2)] p-3.5">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${status.value === "pending" ? "bg-[var(--neu)]" : status.value === "approved" ? "bg-[var(--pos)]" : "bg-[var(--neg)]"}`} />
                    <span className="text-[13.5px] font-bold">{status.label}</span>
                  </div>
                  <span className="grid h-6 min-w-6 place-items-center rounded-full bg-[var(--surface)] px-2 text-xs font-extrabold text-[var(--text-2)]">{rows.length}</span>
                </div>
                <div className="space-y-2">
                  {loading ? Array.from({ length: 2 }).map((_, index) => <Card key={index} className="h-24 animate-pulse bg-[var(--surface)] shadow-none" />) : rows.length ? rows.map((request) => (
                    <button
                      key={request.request_id}
                      onClick={() => setRequestModal(request)}
                      className="w-full rounded-[11px] border border-[var(--border)] bg-[var(--surface)] p-3 text-left shadow-[var(--shadow-sm)] transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)]"
                    >
                      <div className="mb-1 truncate text-[11.5px] font-bold text-[var(--primary)]">{request.product_id}</div>
                      <div className="line-clamp-2 text-[13.5px] font-bold leading-snug text-[var(--text)]">
                        {request.proposed_description || request.proposed_official_url || request.proposed_image_url || "Cập nhật thông số kỹ thuật"}
                      </div>
                      <div className="mt-2 flex items-center justify-between gap-2 text-[11.5px] font-semibold text-[var(--text-3)]">
                        <span className="truncate">{request.submitted_by}</span>
                        <span className="num shrink-0">{formatDate(request.created_at)}</span>
                      </div>
                    </button>
                  )) : (
                    <div className="py-8 text-center text-[12.5px] font-medium text-[var(--text-3)]">Chưa có phiếu</div>
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}

      <Modal open={productModalOpen} title="Thêm sản phẩm" onClose={() => setProductModalOpen(false)}>
        <form onSubmit={(event) => { event.preventDefault(); void createProduct(); }} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Mã sản phẩm</label>
            <Input value={productForm.product_id} onChange={(event) => setProductForm((form) => ({ ...form, product_id: event.target.value }))} placeholder="Tự sinh từ tên nếu để trống" />
          </div>
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Tên model *</label>
            <Input required value={productForm.product_name} onChange={(event) => setProductForm((form) => ({ ...form, product_name: event.target.value }))} placeholder="vd: iPhone 17 Pro Max" />
          </div>
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Hãng</label>
            <Input value={productForm.brand} onChange={(event) => setProductForm((form) => ({ ...form, brand: event.target.value }))} placeholder="vd: Apple" />
          </div>
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Danh mục</label>
            <Dropdown value={productForm.category} onChange={(event) => setProductForm((form) => ({ ...form, category: event.target.value }))} options={categoryOptions} placeholder="Chọn danh mục có sẵn" />
            <Input className="mt-2" value={productForm.category} onChange={(event) => setProductForm((form) => ({ ...form, category: event.target.value }))} placeholder="Hoặc nhập danh mục mới" />
          </div>
          <div>
            <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Năm phát hành</label>
            <Input type="number" value={productForm.release_year} onChange={(event) => setProductForm((form) => ({ ...form, release_year: event.target.value }))} placeholder="2026" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setProductModalOpen(false)}>Hủy</Button>
            <Button type="submit" disabled={savingProduct || !productForm.product_name.trim()}>{savingProduct ? "Đang lưu..." : "Thêm sản phẩm"}</Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!requestModal} title="Chi tiết phiếu chỉnh sửa" onClose={() => setRequestModal(null)}>
        {requestModal && (
          <div className="space-y-4">
            <div className="rounded-[10px] bg-[var(--surface-2)] p-3">
              <div className="mb-1 text-xs text-[var(--text-3)]">Sản phẩm</div>
              <div className="num font-bold text-[var(--primary)]">{requestModal.product_id}</div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--text-3)]">
                <Badge variant={statusVariant(requestModal.status)}>{statusLabel(requestModal.status)}</Badge>
                <span>{requestModal.submitted_by}</span>
                <span className="num">{formatDate(requestModal.created_at)}</span>
              </div>
            </div>
            {requestModal.proposed_description && (
              <div>
                <div className="mb-1 text-[12.5px] font-bold text-[var(--text-2)]">Mô tả đề xuất</div>
                <p className="rounded-[10px] bg-[var(--surface-2)] p-3 text-sm text-[var(--text)]">{requestModal.proposed_description}</p>
              </div>
            )}
            {(requestModal.proposed_official_url || requestModal.proposed_image_url) && (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <div className="mb-1 text-[12.5px] font-bold text-[var(--text-2)]">Official URL</div>
                  <div className="num break-all rounded-[10px] bg-[var(--surface-2)] p-3 text-xs text-[var(--text-2)]">{requestModal.proposed_official_url || "—"}</div>
                </div>
                <div>
                  <div className="mb-1 text-[12.5px] font-bold text-[var(--text-2)]">Image URL</div>
                  <div className="num break-all rounded-[10px] bg-[var(--surface-2)] p-3 text-xs text-[var(--text-2)]">{requestModal.proposed_image_url || "—"}</div>
                </div>
              </div>
            )}
            <div>
              <div className="mb-1 text-[12.5px] font-bold text-[var(--text-2)]">Thông số đề xuất</div>
              <pre className="max-h-64 overflow-auto rounded-[10px] bg-[var(--code-bg)] p-3 text-xs text-[var(--text-2)]">{JSON.stringify(requestModal.proposed_specs ?? {}, null, 2)}</pre>
            </div>
            {requestModal.status === "pending" && (
              <div className="flex justify-end gap-3 pt-2">
                <Button variant="destructive" disabled={reviewingId === requestModal.request_id} onClick={() => void reviewRequest(requestModal.request_id, "reject")}>Từ chối</Button>
                <Button variant="success" disabled={reviewingId === requestModal.request_id} onClick={() => void reviewRequest(requestModal.request_id, "approve")}>Duyệt</Button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
