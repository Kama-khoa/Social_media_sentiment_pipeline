"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ComponentProps } from "react";
import { api } from "@/lib/api-client";
import type { ProductConfigItem, ProductResolutionCandidate } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";

const statuses = [
  { value: "pending", label: "Chờ duyệt", variant: "warning" },
  { value: "approved", label: "Đã duyệt", variant: "success" },
  { value: "rejected", label: "Từ chối", variant: "destructive" },
] as const;

const sentimentOptions = [
  { value: "NEUTRAL", label: "Trung tính (NEUTRAL)" },
  { value: "POSITIVE", label: "Tích cực (POSITIVE)" },
  { value: "NEGATIVE", label: "Tiêu cực (NEGATIVE)" },
];

function sourceLabel(value: string) {
  if (value === "video") return "Video";
  if (value === "sentence") return "Câu bình luận";
  return value;
}

function statusLabel(value: string) {
  return statuses.find((item) => item.value === value)?.label ?? value;
}

function statusVariant(value: string): ComponentProps<typeof Badge>["variant"] {
  return statuses.find((item) => item.value === value)?.variant ?? "secondary";
}

export default function ProductCandidatesPage() {
  const [products, setProducts] = useState<ProductConfigItem[]>([]);
  const [candidates, setCandidates] = useState<ProductResolutionCandidate[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({ pending: 0, approved: 0, rejected: 0 });
  const [status, setStatus] = useState("pending");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;
  const prefetchCache = useRef<Record<string, ProductResolutionCandidate[]>>({});
  const [reviewTarget, setReviewTarget] = useState<ProductResolutionCandidate | null>(null);
  const [form, setForm] = useState({ product_id: "", alias_text: "", sentiment_label: "NEUTRAL" });
  const [productSearch, setProductSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const productNameById = useMemo(
    () => new Map(products.map((item) => [item.product_id, item.product_name])),
    [products],
  );
  const productOptions = useMemo(() => {
    const term = productSearch.trim().toLowerCase();
    const filtered = term
      ? products.filter((product) => product.product_name.toLowerCase().includes(term) || product.product_id.toLowerCase().includes(term))
      : products;
    return filtered.slice(0, 30).map((product) => ({ value: product.product_id, label: `${product.product_name} (${product.product_id})` }));
  }, [productSearch, products]);

  const loadData = useCallback(async (currentStatus: string, currentPage: number, forceRefresh = false) => {
    setLoading(true);
    try {
      if (products.length === 0 || forceRefresh) {
        const [nextProducts, nextCounts] = await Promise.all([
          api.admin.products.list(),
          api.admin.products.candidateCounts(),
        ]);
        setProducts(nextProducts);
        setCounts({ pending: nextCounts.pending || 0, approved: nextCounts.approved || 0, rejected: nextCounts.rejected || 0 });
      }

      const cacheKey = `${currentStatus}_${currentPage}`;
      let nextCandidates = prefetchCache.current[cacheKey];
      if (!nextCandidates || forceRefresh) {
        nextCandidates = await api.admin.products.candidates(currentStatus, currentPage, PAGE_SIZE);
        prefetchCache.current[cacheKey] = nextCandidates;
      }
      setCandidates(nextCandidates);
      setError(null);
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể tải danh sách candidate.");
    } finally {
      setLoading(false);
    }
  }, [products.length]);

  useEffect(() => {
    void loadData(status, page);
  }, [status, page, loadData]);

  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil((counts[status] || 0) / PAGE_SIZE));
    if (page < totalPages) {
      const cacheKey = `${status}_${page + 1}`;
      if (!prefetchCache.current[cacheKey]) {
        api.admin.products.candidates(status, page + 1, PAGE_SIZE)
          .then(data => { prefetchCache.current[cacheKey] = data; })
          .catch(() => {});
      }
    }
  }, [status, page, counts]);

  function openReview(candidate: ProductResolutionCandidate) {
    setReviewTarget(candidate);
    setForm({ product_id: "", alias_text: "", sentiment_label: "NEUTRAL" });
    setProductSearch(candidate.candidate_text);
  }

  async function approveCandidate() {
    if (!reviewTarget || !form.product_id) return;
    setSaving(true);
    try {
      await api.admin.products.reviewCandidate(
        reviewTarget.candidate_id,
        form.product_id,
        form.alias_text.trim() || undefined,
        reviewTarget.source_type === "sentence" ? form.sentiment_label as "POSITIVE" | "NEGATIVE" | "NEUTRAL" : undefined,
      );
      setReviewTarget(null);
      prefetchCache.current = {};
      await loadData(status, page, true);
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể duyệt candidate.");
    } finally {
      setSaving(false);
    }
  }

  async function rejectCandidate(candidate: ProductResolutionCandidate) {
    const confirmed = window.confirm("Từ chối candidate này?");
    if (!confirmed) return;
    try {
      await api.admin.products.rejectCandidate(candidate.candidate_id);
      prefetchCache.current = {};
      await loadData(status, page, true);
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể từ chối candidate.");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Duyệt ánh xạ sản phẩm"
        description="Văn bản hoặc video chưa khớp chắc chắn với catalog, cần Admin ánh xạ thủ công."
      />

      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

      <div className="flex flex-wrap gap-1.5">
        {statuses.map((item) => (
          <button
            key={item.value}
            onClick={() => { setStatus(item.value); setPage(1); }}
            className={`rounded-[10px] px-4 py-2 text-[13.5px] font-semibold shadow-[var(--shadow-sm)] transition-all ${status === item.value ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-none" : "bg-[var(--surface)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
          >
            {item.label}<span className="ml-2 opacity-70">{counts[item.value] ?? 0}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, index) => <Card key={index} className="h-24 animate-pulse bg-[var(--surface-2)] shadow-none" />)}
        </div>
      ) : candidates.length === 0 ? (
        <Card className="py-12 text-center shadow-none">
          <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-[14px] bg-[var(--surface-3)] text-[var(--text-3)]"><Icon name="inbox" size={24} /></div>
          <div className="font-bold text-[var(--text-2)]">Không có candidate ở trạng thái này.</div>
        </Card>
      ) : (
        <>
          <div className="space-y-2.5">
            {candidates.map((candidate) => (
              <Card key={candidate.candidate_id} className="flex flex-wrap items-center justify-between gap-4 p-4 shadow-none">
                <div className="min-w-[260px] flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <code className="num rounded-lg bg-[var(--code-bg)] px-3 py-1.5 text-sm font-bold text-[var(--primary)]">{candidate.candidate_text}</code>
                    <Badge variant={candidate.source_type === "video" ? "brand" : "secondary"}>{sourceLabel(candidate.source_type)}</Badge>
                    <Badge variant={statusVariant(candidate.status)}>{statusLabel(candidate.status)}</Badge>
                  </div>
                  <div className="num text-[12.5px] text-[var(--text-3)]">source_id: {candidate.source_id} · {new Date(candidate.created_at).toLocaleString("vi-VN")}</div>
                  {candidate.resolved_product_id && (
                    <div className="mt-2 flex items-center gap-1.5 text-sm font-bold text-[var(--pos)]">
                      <Icon name="check" size={14} />{productNameById.get(candidate.resolved_product_id) ?? candidate.resolved_product_id}
                    </div>
                  )}
                  {(candidate.resolver_reason || candidate.resolution_method) && (
                    <div className="mt-1 text-xs text-[var(--text-3)]">{candidate.resolution_method ?? "resolver"} · {candidate.resolver_reason ?? "—"}</div>
                  )}
                </div>
                {candidate.status === "pending" && (
                  <div className="flex gap-2">
                    <Button className="bg-[var(--pos)] text-white hover:brightness-95" onClick={() => openReview(candidate)}><Icon name="check" size={16} />Duyệt</Button>
                    <Button variant="outline" onClick={() => void rejectCandidate(candidate)}><Icon name="close" size={16} />Từ chối</Button>
                  </div>
                )}
              </Card>
            ))}
          </div>

          {!loading && candidates.length > 0 && (
            <Card className="mt-4 flex flex-wrap items-center justify-between gap-3 px-4 py-3 shadow-none text-xs text-[var(--text-3)] border border-slate-100 bg-white">
              <span>
                Hiển thị {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, counts[status] || 0)} · {counts[status] || 0} tổng cộng
              </span>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Trước</Button>
                <span className="num text-[var(--text-2)] font-medium text-slate-500">Trang {page}/{Math.max(1, Math.ceil((counts[status] || 0) / PAGE_SIZE))}</span>
                <Button variant="outline" size="sm" disabled={page >= Math.max(1, Math.ceil((counts[status] || 0) / PAGE_SIZE))} onClick={() => setPage((current) => Math.min(Math.max(1, Math.ceil((counts[status] || 0) / PAGE_SIZE)), current + 1))}>Sau</Button>
              </div>
            </Card>
          )}
        </>
      )}

      <Modal open={!!reviewTarget} title="Xác nhận duyệt candidate" onClose={() => setReviewTarget(null)}>
        {reviewTarget && (
          <form onSubmit={(event) => { event.preventDefault(); void approveCandidate(); }} className="space-y-4">
            <div className="rounded-[10px] bg-[var(--surface-2)] p-3">
              <div className="mb-1 text-xs text-[var(--text-3)]">Candidate text</div>
              <code className="num text-sm font-bold text-[var(--primary)]">{reviewTarget.candidate_text}</code>
              <div className="mt-2 text-xs text-[var(--text-3)]">{sourceLabel(reviewTarget.source_type)} · {reviewTarget.source_id}</div>
            </div>
            <div>
              <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Tìm sản phẩm</label>
              <Input value={productSearch} onChange={(event) => setProductSearch(event.target.value)} placeholder="Nhập tên sản phẩm hoặc ID..." />
            </div>
            <div>
              <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Ánh xạ đến sản phẩm *</label>
              <Dropdown value={form.product_id} onChange={(event) => setForm((current) => ({ ...current, product_id: event.target.value }))} options={productOptions} placeholder="Chọn sản phẩm" />
            </div>
            <div>
              <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Alias mới cho model này</label>
              <Input value={form.alias_text} onChange={(event) => setForm((current) => ({ ...current, alias_text: event.target.value }))} placeholder="Tùy chọn" />
            </div>
            {reviewTarget.source_type === "sentence" && (
              <div>
                <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Sắc thái cảm xúc</label>
                <Dropdown value={form.sentiment_label} onChange={(event) => setForm((current) => ({ ...current, sentiment_label: event.target.value }))} options={sentimentOptions} />
              </div>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={() => setReviewTarget(null)}>Hủy</Button>
              <Button type="submit" disabled={saving || !form.product_id}><Icon name="check" size={16} />{saving ? "Đang duyệt..." : "Xác nhận duyệt"}</Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
