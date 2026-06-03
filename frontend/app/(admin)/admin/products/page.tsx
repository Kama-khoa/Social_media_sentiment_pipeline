"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api-client";
import type {
  ProductAliasItem,
  ProductConfigItem,
  ProductDetailChangeRequestItem,
  ProductSpecTemplateItem,
  ProductResolutionCandidate,
} from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/PageHeader";

const PAGE_SIZE = 10;
const PREFETCH_AHEAD = 5;
const MAX_CACHED_PAGES = 20;

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

function slicePage<T>(items: T[], page: number) {
  const start = (page - 1) * PAGE_SIZE;
  return items.slice(start, start + PAGE_SIZE);
}

function totalPagesFor(items: unknown[]) {
  return Math.max(1, Math.ceil(items.length / PAGE_SIZE));
}

function buildPageCache<T>(items: T[], centerPage: number) {
  const maxPage = totalPagesFor(items);
  const start = Math.max(1, centerPage - PREFETCH_AHEAD);
  const end = Math.min(maxPage, start + MAX_CACHED_PAGES - 1);
  const nextCache: Record<number, T[]> = {};
  for (let page = start; page <= end; page += 1) {
    nextCache[page] = slicePage(items, page);
  }
  return nextCache;
}

function pageOptionsFor(totalPages: number) {
  return Array.from({ length: totalPages }, (_, index) => ({ value: String(index + 1), label: `Trang ${index + 1}` }));
}

function candidateSourceLabel(sourceType: string) {
  return sourceType === "video" ? "Video" : sourceType === "sentence" ? "Câu bình luận" : sourceType;
}

export default function ProductsAdminPage() {
  const [products, setProducts] = useState<ProductConfigItem[]>([]);
  const [aliases, setAliases] = useState<ProductAliasItem[]>([]);
  const [templates, setTemplates] = useState<ProductSpecTemplateItem[]>([]);
  const [requests, setRequests] = useState<ProductDetailChangeRequestItem[]>([]);
  const [candidates, setCandidates] = useState<ProductResolutionCandidate[]>([]);
  const [productPageCache, setProductPageCache] = useState<Record<number, ProductConfigItem[]>>({});
  const [aliasPageCache, setAliasPageCache] = useState<Record<number, ProductAliasItem[]>>({});
  const [templatePageCache, setTemplatePageCache] = useState<Record<number, ProductSpecTemplateItem[]>>({});
  const [candidatePageCache, setCandidatePageCache] = useState<Record<number, ProductResolutionCandidate[]>>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [aliasPage, setAliasPage] = useState(1);
  const [templatePage, setTemplatePage] = useState(1);
  const [candidatePage, setCandidatePage] = useState(1);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [productModalOpen, setProductModalOpen] = useState(false);
  const [savingProduct, setSavingProduct] = useState(false);
  const [productForm, setProductForm] = useState<ProductForm>(emptyProductForm);
  const [aliasProductId, setAliasProductId] = useState("");
  const [aliasText, setAliasText] = useState("");
  const [templateCategory, setTemplateCategory] = useState("");
  const [templateKey, setTemplateKey] = useState("");
  const [templateLabel, setTemplateLabel] = useState("");
  const [resolveModalOpen, setResolveModalOpen] = useState(false);
  const [currentCandidate, setCurrentCandidate] = useState<ProductResolutionCandidate | null>(null);
  const [resolveForm, setResolveForm] = useState({ productId: "", alias: "", sentiment: "NEUTRAL" });
  const [productSearchTerm, setProductSearchTerm] = useState("");

  const categories = useMemo(() => Array.from(new Set(products.map((item) => item.category).filter(Boolean) as string[])).sort((a, b) => a.localeCompare(b, "vi")), [products]);
  const categoryOptions = useMemo(() => categories.map((category) => ({ value: category, label: category })), [categories]);
  const filteredProducts = useMemo(
    () => categoryFilter ? products.filter((item) => item.category === categoryFilter) : products,
    [categoryFilter, products],
  );
  const totalPages = Math.max(1, Math.ceil(filteredProducts.length / PAGE_SIZE));
  const visibleProducts = productPageCache[currentPage] ?? slicePage(filteredProducts, currentPage);
  const pageOptions = useMemo(() => pageOptionsFor(totalPages), [totalPages]);
  const aliasTotalPages = totalPagesFor(aliases);
  const templateTotalPages = totalPagesFor(templates);
  const candidateTotalPages = totalPagesFor(candidates);
  const visibleAliases = aliasPageCache[aliasPage] ?? slicePage(aliases, aliasPage);
  const visibleTemplates = templatePageCache[templatePage] ?? slicePage(templates, templatePage);
  const visibleCandidates = candidatePageCache[candidatePage] ?? slicePage(candidates, candidatePage);
  const aliasPageOptions = useMemo(() => pageOptionsFor(aliasTotalPages), [aliasTotalPages]);
  const templatePageOptions = useMemo(() => pageOptionsFor(templateTotalPages), [templateTotalPages]);
  const candidatePageOptions = useMemo(() => pageOptionsFor(candidateTotalPages), [candidateTotalPages]);

  const warmProductPageCache = useCallback((items: ProductConfigItem[], centerPage: number) => {
    setProductPageCache(buildPageCache(items, centerPage));
  }, []);

  const load = useCallback(async (cachePage = 1) => {
    setLoading(true);
    try {
      const [nextProducts, nextAliases, nextTemplates, nextRequests, nextCandidates] = await Promise.all([
        api.admin.products.list(),
        api.admin.products.aliases(),
        api.admin.products.templates(),
        api.admin.products.detailRequests(),
        api.admin.products.candidates(),
      ]);
      setProducts(nextProducts);
      setAliases(nextAliases);
      setTemplates(nextTemplates);
      setRequests(nextRequests);
      setCandidates(nextCandidates);
      setError(null);
      warmProductPageCache(nextProducts, cachePage);
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail ?? "Không thể tải catalog sản phẩm.");
    } finally {
      setLoading(false);
    }
  }, [warmProductPageCache]);

  useEffect(() => { void load(1); }, [load]);

  useEffect(() => {
    const boundedPage = Math.min(currentPage, totalPages);
    if (boundedPage !== currentPage) {
      setCurrentPage(boundedPage);
      return;
    }
    warmProductPageCache(filteredProducts, boundedPage);
  }, [categoryFilter, currentPage, filteredProducts, totalPages, warmProductPageCache]);

  useEffect(() => {
    const boundedPage = Math.min(aliasPage, aliasTotalPages);
    if (boundedPage !== aliasPage) {
      setAliasPage(boundedPage);
      return;
    }
    setAliasPageCache(buildPageCache(aliases, boundedPage));
  }, [aliasPage, aliasTotalPages, aliases]);

  useEffect(() => {
    const boundedPage = Math.min(templatePage, templateTotalPages);
    if (boundedPage !== templatePage) {
      setTemplatePage(boundedPage);
      return;
    }
    setTemplatePageCache(buildPageCache(templates, boundedPage));
  }, [templatePage, templateTotalPages, templates]);

  useEffect(() => {
    const boundedPage = Math.min(candidatePage, candidateTotalPages);
    if (boundedPage !== candidatePage) {
      setCandidatePage(boundedPage);
      return;
    }
    setCandidatePageCache(buildPageCache(candidates, boundedPage));
  }, [candidatePage, candidateTotalPages, candidates]);

  async function review(id: string, action: "approve" | "reject") {
    await api.admin.products.reviewDetailRequest(id, action);
    await load(currentPage);
  }

  async function createProduct() {
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
      await load(currentPage);
    } finally {
      setSavingProduct(false);
    }
  }

  async function createAlias() {
    await api.admin.products.createAlias({ product_id: aliasProductId, alias_text: aliasText });
    setAliasText("");
    await load(currentPage);
  }

  async function createTemplate() {
    await api.admin.products.createTemplate({ category: templateCategory, spec_key: templateKey, display_label: templateLabel, value_type: "string" });
    setTemplateKey("");
    setTemplateLabel("");
    await load(currentPage);
  }

  function openResolveModal(item: ProductResolutionCandidate) {
    setCurrentCandidate(item);
    setResolveForm({ productId: "", alias: "", sentiment: "NEUTRAL" });
    setProductSearchTerm("");
    setResolveModalOpen(true);
  }

  async function submitResolve() {
    if (!currentCandidate || !resolveForm.productId) return;
    
    await api.admin.products.reviewCandidate(
      currentCandidate.candidate_id,
      resolveForm.productId,
      resolveForm.alias || undefined,
      currentCandidate.source_type === "sentence" ? resolveForm.sentiment as "POSITIVE" | "NEGATIVE" | "NEUTRAL" : undefined,
    );
    setResolveModalOpen(false);
    await load(currentPage);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Catalog sản phẩm"
        description="Theo dõi model chuẩn, alias, template specs và đề xuất từ người dùng."
        action={<Button onClick={() => setProductModalOpen(true)}>Thêm sản phẩm</Button>}
      />
      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

      <Card className="overflow-hidden shadow-none">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div>
            <h2 className="font-medium text-slate-700">Sản phẩm ({filteredProducts.length})</h2>
            <p className="mt-1 text-xs text-slate-400">10 bản ghi/trang · cache {Object.keys(productPageCache).length} trang gần vị trí hiện tại</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Dropdown value={categoryFilter} onChange={(event) => { setCategoryFilter(event.target.value); setCurrentPage(1); }} options={categoryOptions} placeholder="Tất cả danh mục" className="w-48" />
            <Dropdown value={String(currentPage)} onChange={(event) => setCurrentPage(Number(event.target.value))} options={pageOptions} className="w-32" />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-slate-100 text-left text-slate-500"><th className="px-4 py-2">Tên</th><th>Hãng</th><th>Danh mục</th><th>Năm</th><th>ID</th></tr></thead>
            <tbody>
              {loading ? Array.from({ length: PAGE_SIZE }).map((_, index) => <tr key={index} className="border-b border-slate-100">{Array.from({ length: 5 }).map((__, cell) => <td key={cell} className="px-4 py-3"><div className="h-4 animate-pulse rounded bg-slate-100" /></td>)}</tr>) : visibleProducts.length ? visibleProducts.map((item) => <tr key={item.product_id} className="border-b border-slate-100"><td className="px-4 py-2 font-medium">{item.product_name}</td><td>{item.brand ?? "-"}</td><td>{item.category ?? "-"}</td><td>{item.release_year ?? "-"}</td><td className="text-xs text-slate-500">{item.product_id}</td></tr>) : <tr><td colSpan={5} className="px-4 py-12 text-center text-sm text-slate-400">Không có sản phẩm phù hợp.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-xs text-slate-400">
          <span>Trang {currentPage}/{totalPages}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={currentPage <= 1} onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}>Trước</Button>
            <Button variant="outline" size="sm" disabled={currentPage >= totalPages} onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}>Sau</Button>
          </div>
        </div>
      </Card>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card className="p-4 space-y-2">
          <h2 className="font-medium text-slate-700">Thêm tên gọi thay thế</h2>
          <Input value={aliasProductId} onChange={(e) => setAliasProductId(e.target.value)} placeholder="Mã sản phẩm" />
          <Input value={aliasText} onChange={(e) => setAliasText(e.target.value)} placeholder="Tên gọi thay thế" />
          <Button onClick={createAlias} size="sm">Thêm tên gọi</Button>
        </Card>
        <Card className="p-4 space-y-2">
          <h2 className="font-medium text-slate-700">Thêm mẫu thông số</h2>
          <Input value={templateCategory} onChange={(e) => setTemplateCategory(e.target.value)} placeholder="Danh mục" />
          <Input value={templateKey} onChange={(e) => setTemplateKey(e.target.value)} placeholder="Mã thông số" />
          <Input value={templateLabel} onChange={(e) => setTemplateLabel(e.target.value)} placeholder="Nhãn hiển thị" />
          <Button onClick={createTemplate} size="sm">Thêm mẫu</Button>
        </Card>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="overflow-hidden shadow-none">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
            <div>
              <h2 className="font-medium text-slate-700">Tên gọi thay thế ({aliases.length})</h2>
              <p className="mt-1 text-xs text-slate-400">10 bản ghi/trang · cache {Object.keys(aliasPageCache).length} trang</p>
            </div>
            <Dropdown value={String(aliasPage)} onChange={(event) => setAliasPage(Number(event.target.value))} options={aliasPageOptions} className="w-32" />
          </div>
          <div className="max-h-80 overflow-auto">
            {visibleAliases.length ? visibleAliases.map((item, index) => <div key={`${item.alias_id}-${item.product_id}-${index}`} className="flex justify-between gap-3 border-b border-slate-100 px-4 py-2 text-sm"><span>{item.alias_text}</span><span className="text-slate-400">{item.product_id}</span></div>) : <div className="px-4 py-10 text-center text-sm text-slate-400">Chưa có tên gọi thay thế.</div>}
          </div>
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-xs text-slate-400"><span>Trang {aliasPage}/{aliasTotalPages}</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={aliasPage <= 1} onClick={() => setAliasPage((page) => Math.max(1, page - 1))}>Trước</Button><Button variant="outline" size="sm" disabled={aliasPage >= aliasTotalPages} onClick={() => setAliasPage((page) => Math.min(aliasTotalPages, page + 1))}>Sau</Button></div></div>
        </Card>
        <Card className="overflow-hidden shadow-none">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
            <div>
              <h2 className="font-medium text-slate-700">Mẫu thông số ({templates.length})</h2>
              <p className="mt-1 text-xs text-slate-400">10 bản ghi/trang · cache {Object.keys(templatePageCache).length} trang</p>
            </div>
            <Dropdown value={String(templatePage)} onChange={(event) => setTemplatePage(Number(event.target.value))} options={templatePageOptions} className="w-32" />
          </div>
          <div className="max-h-80 overflow-auto">
            {visibleTemplates.length ? visibleTemplates.map((item, index) => <div key={`${item.category}-${item.spec_key}-${index}`} className="flex justify-between gap-3 border-b border-slate-100 px-4 py-2 text-sm"><span>{item.category}: {item.display_label}</span><span className="text-slate-400">{item.value_type}{item.unit ? ` (${item.unit})` : ""}</span></div>) : <div className="px-4 py-10 text-center text-sm text-slate-400">Chưa có mẫu thông số.</div>}
          </div>
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-xs text-slate-400"><span>Trang {templatePage}/{templateTotalPages}</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={templatePage <= 1} onClick={() => setTemplatePage((page) => Math.max(1, page - 1))}>Trước</Button><Button variant="outline" size="sm" disabled={templatePage >= templateTotalPages} onClick={() => setTemplatePage((page) => Math.min(templateTotalPages, page + 1))}>Sau</Button></div></div>
        </Card>
      </div>

      <Card className="p-4 shadow-none">
        <h2 className="font-medium text-slate-700">Đề xuất đang chờ duyệt ({requests.length})</h2>
        <div className="mt-3 space-y-3">
          {requests.length === 0 && <p className="text-sm text-slate-400">Không có đề xuất đang chờ.</p>}
          {requests.map((item) => (
            <div key={item.request_id} className="border border-slate-200 rounded-lg p-3 text-sm">
              <div className="font-medium text-slate-700">{item.product_id}</div>
              <pre className="mt-2 text-xs bg-slate-50 rounded p-2 overflow-auto">{JSON.stringify(item.proposed_specs, null, 2)}</pre>
              <div className="flex gap-2 mt-3">
                <Button onClick={() => review(item.request_id, "approve")} variant="success" size="sm">Duyệt</Button>
                <Button onClick={() => review(item.request_id, "reject")} variant="destructive" size="sm">Từ chối</Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="overflow-hidden shadow-none">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div>
            <h2 className="font-medium text-slate-700">Ứng viên cần phân giải ({candidates.length})</h2>
            <p className="mt-1 text-xs text-slate-400">10 bản ghi/trang · cache {Object.keys(candidatePageCache).length} trang</p>
          </div>
          <Dropdown value={String(candidatePage)} onChange={(event) => setCandidatePage(Number(event.target.value))} options={candidatePageOptions} className="w-32" />
        </div>
        <div className="space-y-2 p-4">
          {visibleCandidates.length === 0 && <p className="text-sm text-slate-400">Không có ứng viên đang chờ.</p>}
          {visibleCandidates.map((item, index) => (
            <div key={`${item.candidate_id}-${item.source_type}-${item.source_id}-${index}`} className="border border-slate-200 rounded-lg p-3 text-sm flex items-center justify-between gap-3">
              <div><Badge variant="secondary">{candidateSourceLabel(item.source_type)}</Badge><p className="mt-1 text-slate-700">{item.candidate_text}</p></div>
              <Button onClick={() => openResolveModal(item)} size="sm" className="shrink-0">Phân giải</Button>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-xs text-slate-400"><span>Trang {candidatePage}/{candidateTotalPages}</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={candidatePage <= 1} onClick={() => setCandidatePage((page) => Math.max(1, page - 1))}>Trước</Button><Button variant="outline" size="sm" disabled={candidatePage >= candidateTotalPages} onClick={() => setCandidatePage((page) => Math.min(candidateTotalPages, page + 1))}>Sau</Button></div></div>
      </Card>

      <Modal open={productModalOpen} title="Thêm sản phẩm" onClose={() => setProductModalOpen(false)}>
        <form onSubmit={(event) => { event.preventDefault(); void createProduct(); }} className="space-y-4">
          <div><label className="mb-1 block text-sm font-medium text-slate-700">Mã sản phẩm</label><Input value={productForm.product_id} onChange={(event) => setProductForm((form) => ({ ...form, product_id: event.target.value }))} placeholder="Tự sinh từ tên nếu để trống" /></div>
          <div><label className="mb-1 block text-sm font-medium text-slate-700">Tên model</label><Input required value={productForm.product_name} onChange={(event) => setProductForm((form) => ({ ...form, product_name: event.target.value }))} placeholder="vd: iPhone 17 Pro Max" /></div>
          <div><label className="mb-1 block text-sm font-medium text-slate-700">Hãng</label><Input value={productForm.brand} onChange={(event) => setProductForm((form) => ({ ...form, brand: event.target.value }))} placeholder="vd: Apple" /></div>
          <div><label className="mb-1 block text-sm font-medium text-slate-700">Danh mục</label><Dropdown value={productForm.category} onChange={(event) => setProductForm((form) => ({ ...form, category: event.target.value }))} options={categoryOptions} placeholder="Chọn hoặc nhập danh mục bên dưới" /></div>
          <Input value={productForm.category} onChange={(event) => setProductForm((form) => ({ ...form, category: event.target.value }))} placeholder="Danh mục mới nếu chưa có trong dropdown" />
          <div><label className="mb-1 block text-sm font-medium text-slate-700">Năm phát hành</label><Input type="number" value={productForm.release_year} onChange={(event) => setProductForm((form) => ({ ...form, release_year: event.target.value }))} placeholder="2026" /></div>
          <div className="flex justify-end gap-3 pt-2"><Button type="button" variant="outline" onClick={() => setProductModalOpen(false)}>Hủy</Button><Button type="submit" disabled={savingProduct}>{savingProduct ? "Đang lưu..." : "Thêm sản phẩm"}</Button></div>
        </form>
      </Modal>

      <Modal open={resolveModalOpen} title="Phân giải ứng viên" onClose={() => setResolveModalOpen(false)}>
        <form onSubmit={(event) => { event.preventDefault(); void submitResolve(); }} className="space-y-4">
          <div className="text-sm font-medium text-slate-700 bg-slate-50 p-2 rounded">
            <div><span className="text-slate-500">Loại:</span> {currentCandidate ? candidateSourceLabel(currentCandidate.source_type) : ""}</div>
            <div className="mt-1"><span className="text-slate-500">Nội dung:</span> {currentCandidate?.candidate_text}</div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Tìm mã sản phẩm</label>
            <Input value={productSearchTerm} onChange={(e) => setProductSearchTerm(e.target.value)} placeholder="Nhập tên sản phẩm hoặc ID để tìm..." className="mb-2" />
            <div className="max-h-32 overflow-auto border border-slate-200 rounded p-1">
              {products
                .filter(p => p.product_name.toLowerCase().includes(productSearchTerm.toLowerCase()) || p.product_id.toLowerCase().includes(productSearchTerm.toLowerCase()))
                .slice(0, 20)
                .map((p, index) => (
                  <div 
                    key={`${p.product_id}-${index}`} 
                    className={`text-xs p-1.5 cursor-pointer hover:bg-slate-100 rounded flex justify-between items-center ${resolveForm.productId === p.product_id ? 'bg-blue-50 border-blue-200 border text-blue-700' : ''}`}
                    onClick={() => setResolveForm(f => ({...f, productId: p.product_id}))}
                  >
                    <span>{p.product_name}</span>
                    <span className="text-slate-400 font-mono">{p.product_id}</span>
                  </div>
                ))}
              {products.length === 0 && <div className="text-xs text-slate-400 p-2 text-center">Chưa có dữ liệu sản phẩm.</div>}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Mã sản phẩm chuẩn</label>
            <Input required value={resolveForm.productId} onChange={(e) => setResolveForm(f => ({ ...f, productId: e.target.value }))} placeholder="vd: iphone-17-pro-max" />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Tên gọi thay thế mới (tùy chọn)</label>
            <Input value={resolveForm.alias} onChange={(e) => setResolveForm(f => ({ ...f, alias: e.target.value }))} placeholder="Thêm alias cho model này để hệ thống học" />
          </div>

          {currentCandidate?.source_type === "sentence" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">Sắc thái cảm xúc</label>
              <Dropdown value={resolveForm.sentiment} onChange={(e) => setResolveForm(f => ({ ...f, sentiment: e.target.value }))} options={[{value: 'POSITIVE', label: 'Tích cực (POSITIVE)'}, {value: 'NEGATIVE', label: 'Tiêu cực (NEGATIVE)'}, {value: 'NEUTRAL', label: 'Trung tính (NEUTRAL)'}]} />
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button type="button" variant="outline" onClick={() => setResolveModalOpen(false)}>Hủy</Button>
            <Button type="submit" disabled={!resolveForm.productId}>Xác nhận phân giải</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
