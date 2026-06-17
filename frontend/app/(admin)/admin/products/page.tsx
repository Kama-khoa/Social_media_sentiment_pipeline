"use client";

import { useCallback, useEffect, useMemo, useState, useRef, type ComponentProps } from "react";
import { api } from "@/lib/api-client";
import type { ProductConfigItem, ProductDetailChangeRequestItem, ProductSpecTemplateItem } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dropdown } from "@/components/ui/dropdown";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";
import { KeywordSuggestionModal } from "@/components/admin/KeywordSuggestionModal";
import { CrawlProgress } from "@/components/admin/CrawlProgress";

const PAGE_SIZE = 10;
const requestStatuses = [
    { value: "pending", label: "Đang chờ", variant: "warning" },
    { value: "processing", label: "Đang xử lý", variant: "default" },
    { value: "approved", label: "Đã tiếp nhận", variant: "success" },
    { value: "rejected", label: "Đã từ chối", variant: "destructive" },
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

function CategoryCombobox({
    value,
    onChange,
    options
}: {
    value: string;
    onChange: (val: string) => void;
    options: { value: string; label: string }[];
}) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState(value);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setSearchTerm(value);
    }, [value]);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const filteredOptions = useMemo(() => {
        if (!searchTerm) return options;
        return options.filter((opt) =>
            opt.label.toLowerCase().includes(searchTerm.toLowerCase())
        );
    }, [options, searchTerm]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setSearchTerm(val);
        onChange(val);
        setIsOpen(true);
    };

    return (
        <div className="relative" ref={containerRef}>
            <div className="relative">
                <Input
                    value={searchTerm}
                    onChange={handleInputChange}
                    onFocus={() => setIsOpen(true)}
                    placeholder="Chọn hoặc nhập danh mục mới..."
                    className="pr-10 font-medium"
                />
                <button
                    type="button"
                    onClick={() => setIsOpen(!isOpen)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-3)] hover:text-[var(--text)] transition-colors"
                >
                    <Icon
                        name="chevron"
                        size={16}
                        style={{
                            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
                            transition: "transform 0.2s ease",
                        }}
                    />
                </button>
            </div>
            {isOpen && (
                <div className="absolute z-50 mt-1.5 w-full max-h-[200px] overflow-y-auto rounded-[12px] border border-[var(--border-strong)] bg-[var(--surface)] p-1.5 shadow-lg">
                    {filteredOptions.length > 0 ? (
                        filteredOptions.map((opt) => (
                            <button
                                key={opt.value}
                                type="button"
                                onClick={() => {
                                    onChange(opt.value);
                                    setSearchTerm(opt.label);
                                    setIsOpen(false);
                                }}
                                className={`w-full rounded-[8px] px-3 py-2 text-left text-[13px] font-medium transition-colors hover:bg-[var(--surface-3)] ${value === opt.value ? "bg-[var(--surface-2)] text-[var(--primary)] font-semibold" : "text-[var(--text-2)]"
                                    }`}
                            >
                                {opt.label}
                            </button>
                        ))
                    ) : (
                        <div className="px-3 py-2 text-center text-xs text-[var(--text-3)] font-medium">
                            Gõ để tự do nhập danh mục mới
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default function ProductsAdminPage() {
    const [tab, setTab] = useState<"catalog" | "requests">("catalog");
    const [products, setProducts] = useState<ProductConfigItem[]>([]);
    const [allCategories, setAllCategories] = useState<string[]>([]);
    const [requests, setRequests] = useState<Record<string, ProductDetailChangeRequestItem[]>>({ pending: [], processing: [], approved: [], rejected: [] });
    const [categoryFilter, setCategoryFilter] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [page, setPage] = useState(1);
    const [totalCount, setTotalCount] = useState(0);
    const [cachedStartPage, setCachedStartPage] = useState(1);
    const [cachedEndPage, setCachedEndPage] = useState(1);
    const [productModalOpen, setProductModalOpen] = useState(false);
    const [requestModal, setRequestModal] = useState<ProductDetailChangeRequestItem | null>(null);
    const [savingProduct, setSavingProduct] = useState(false);
    const [reviewingId, setReviewingId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [productForm, setProductForm] = useState<ProductForm>(emptyProductForm);
    const [draggingId, setDraggingId] = useState<string | null>(null);
    const [suggestProductId, setSuggestProductId] = useState<string | null>(null);
    const [specs, setSpecs] = useState<{
        key: string;
        label?: string;
        value: string;
        value_type?: string;
        unit?: string | null;
        isFromTemplate?: boolean;
    }[]>([]);
    const [templates, setTemplates] = useState<ProductSpecTemplateItem[]>([]);
    const [syncingProductId, setSyncingProductId] = useState<string | null>(null);
    const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
    const [crawlProgressOpen, setCrawlProgressOpen] = useState(false);
    const [crawlProductName, setCrawlProductName] = useState("");
    const [quotaConfirmProduct, setQuotaConfirmProduct] = useState<{ id: string; name: string } | null>(null);

    const categoryOptions = useMemo(
        () => allCategories.map((category) => ({ value: category, label: category })),
        [allCategories],
    );

    const totalPages = pageCount(totalCount);
    const pageStart = (page - 1) * PAGE_SIZE;

    const visibleProducts = useMemo(() => {
        const pageOffsetInCache = (page - cachedStartPage) * PAGE_SIZE;
        if (pageOffsetInCache < 0 || pageOffsetInCache >= products.length) {
            return [];
        }
        return products.slice(pageOffsetInCache, pageOffsetInCache + PAGE_SIZE);
    }, [page, cachedStartPage, products]);

    const pendingRequestCount = requests.pending?.length ?? 0;

    const loadProducts = useCallback(async (targetPage: number, forceReload = false) => {
        setLoading(true);
        try {
            const isCached = !forceReload &&
                targetPage >= cachedStartPage &&
                targetPage <= cachedEndPage &&
                products.length > 0;

            if (!isCached) {
                const limit = PAGE_SIZE * 6; // Load 6 trang (trang hiện tại + 5 trang prefetch)
                const offset = (targetPage - 1) * PAGE_SIZE;

                const [fetchedProducts, countRes] = await Promise.all([
                    api.admin.products.list({
                        limit,
                        offset,
                        category: categoryFilter || undefined,
                        q: searchQuery.trim() || undefined
                    }),
                    api.admin.products.count({
                        category: categoryFilter || undefined,
                        q: searchQuery.trim() || undefined
                    })
                ]);

                setProducts(fetchedProducts);
                setTotalCount(countRes.count);
                setCachedStartPage(targetPage);
                setCachedEndPage(targetPage + 5);
            }
            setError(null);
        } catch (err: unknown) {
            const e = err as { detail?: string };
            setError(e?.detail ?? "Không thể tải catalog sản phẩm.");
        } finally {
            setLoading(false);
        }
    }, [categoryFilter, searchQuery, cachedStartPage, cachedEndPage, products]);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [fullProducts, pending, processing, approved, rejected, nextTemplates] = await Promise.all([
                api.admin.products.list(), // lấy full một lần duy nhất lúc load để tạo category options
                api.admin.products.detailRequests("pending"),
                api.admin.products.detailRequests("processing"),
                api.admin.products.detailRequests("approved"),
                api.admin.products.detailRequests("rejected"),
                api.admin.products.templates(),
            ]);
            
            const cats = Array.from(new Set(fullProducts.map((item) => item.category).filter(Boolean) as string[])).sort((a, b) => a.localeCompare(b, "vi"));
            setAllCategories(cats);
            
            setRequests({ pending, processing, approved, rejected });
            setTemplates(nextTemplates || []);
            setError(null);
        } catch (err: unknown) {
            const e = err as { detail?: string };
            setError(e?.detail ?? "Không thể tải catalog sản phẩm.");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { void load(); }, [load]);
    useEffect(() => { void loadProducts(page); }, [page, categoryFilter, searchQuery, loadProducts]);
    useEffect(() => { setPage(1); }, [categoryFilter, searchQuery]);
    useEffect(() => { setPage((current) => Math.min(current, totalPages)); }, [totalPages]);

    useEffect(() => {
        if (!productModalOpen) {
            setProductForm(emptyProductForm);
            setSpecs([]);
        }
    }, [productModalOpen]);

    useEffect(() => {
        if (!productForm.category) {
            setSpecs([]);
            return;
        }
        const categoryTemplates = templates.filter(
            (t) => t.category.toLowerCase() === productForm.category.toLowerCase()
        );
        if (categoryTemplates.length > 0) {
            setSpecs(
                categoryTemplates.map((t) => ({
                    key: t.spec_key,
                    label: t.display_label,
                    value: "",
                    value_type: t.value_type,
                    unit: t.unit,
                    isFromTemplate: true
                }))
            );
        } else {
            setSpecs([]);
        }
    }, [productForm.category, templates]);

    async function createProduct() {
        if (!productForm.product_name.trim()) return;
        setSavingProduct(true);
        try {
            const specsObj: Record<string, any> = {};
            specs.forEach((item) => {
                const k = item.key.trim();
                const v = item.value.trim();
                if (k && v) {
                    if (v.toLowerCase() === "true") specsObj[k] = true;
                    else if (v.toLowerCase() === "false") specsObj[k] = false;
                    else if (!isNaN(Number(v)) && v !== "") specsObj[k] = Number(v);
                    else specsObj[k] = v;
                }
            });

            await api.admin.products.create({
                product_id: undefined, // Không cần điền mã sản phẩm nữa, backend tự slugify từ name
                product_name: productForm.product_name.trim(),
                brand: productForm.brand.trim() || undefined,
                category: productForm.category.trim() || undefined,
                release_year: productForm.release_year ? Number(productForm.release_year) : undefined,
                specs: Object.keys(specsObj).length > 0 ? specsObj : undefined,
            });
            setProductForm(emptyProductForm);
            setSpecs([]);
            setProductModalOpen(false);
            await load();
            await loadProducts(page, true);
        } catch (err: unknown) {
            const e = err as { detail?: string };
            setError(e?.detail ?? "Không thể thêm sản phẩm.");
        } finally {
            setSavingProduct(false);
        }
    }

    async function toggleProductActive(productId: string, currentStatus: boolean) {
        try {
            setProducts((prev) =>
                prev.map((item) =>
                    item.product_id === productId ? { ...item, is_active: !currentStatus } : item
                )
            );
            await api.admin.products.update(productId, { is_active: !currentStatus });
        } catch (err: unknown) {
            console.error(err);
            const e = err as { detail?: string };
            alert(e?.detail ?? "Không thể thay đổi trạng thái sản phẩm.");
            await loadProducts(page, true);
        }
    }

    async function handleSyncProduct(productId: string) {
        setSyncingProductId(productId);
        try {
            await api.admin.products.sync(productId);
            alert("Đã bắt đầu tiến trình đồng bộ sản phẩm lên dim_product!");
            await loadProducts(page, true);
        } catch (err: any) {
            console.error(err);
            alert(err?.detail ?? "Không thể đồng bộ sản phẩm.");
        } finally {
            setSyncingProductId(null);
        }
    }

    async function handleCrawlProduct(productId: string, productName: string, useYtdlp = false) {
        try {
            setQuotaConfirmProduct(null);
            const res = await api.admin.products.crawl(productId, useYtdlp);
            if (res.status === "quota_exhausted") {
                setQuotaConfirmProduct({ id: productId, name: productName });
            } else if (res.task_id) {
                setCrawlProductName(productName);
                setActiveTaskId(res.task_id);
                setCrawlProgressOpen(true);
            }
        } catch (err: any) {
            console.error(err);
            alert(err?.detail ?? "Không thể bắt đầu thu thập dữ liệu.");
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

    async function handleDrop(e: React.DragEvent, newStatus: string) {
        e.preventDefault();
        if (!draggingId) return;

        let currentStatus = "";
        let draggedRequest: ProductDetailChangeRequestItem | undefined;

        for (const [status, items] of Object.entries(requests)) {
            const found = items.find((r) => r.request_id === draggingId);
            if (found) {
                currentStatus = status;
                draggedRequest = found;
                break;
            }
        }

        if (!draggedRequest || currentStatus === newStatus) {
            setDraggingId(null);
            return;
        }

        if (newStatus === "pending") {
            setDraggingId(null);
            return;
        }

        let action: "approve" | "reject" | "processing";
        if (newStatus === "processing") action = "processing";
        else if (newStatus === "approved") action = "approve";
        else if (newStatus === "rejected") action = "reject";
        else return;

        // Optimistic UI Update
        setRequests((prev) => {
            const next = { ...prev };
            next[currentStatus] = next[currentStatus].filter((r) => r.request_id !== draggingId);
            next[newStatus] = [{ ...draggedRequest!, status: newStatus as any }, ...next[newStatus]];
            return next;
        });

        setDraggingId(null);

        try {
            await api.admin.products.reviewDetailRequest(draggingId, action);
        } catch (err) {
            console.error(err);
            alert("Lỗi khi chuyển trạng thái phiếu");
            await load();
        }
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title="Quản lý sản phẩm"
                description="Catalog sản phẩm và phiếu đề xuất chỉnh sửa thông tin từ người dùng."
            />

            {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</div>}

            <div className="flex flex-wrap items-center justify-between gap-3">
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
                <Button onClick={() => setProductModalOpen(true)}>
                    <Icon name="plus" size={16} className="mr-1.5" />
                    Thêm sản phẩm
                </Button>
            </div>

            {tab === "catalog" ? (
                <Card className="overflow-hidden shadow-none">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-3">
                        <div>
                            <h2 className="font-bold text-[var(--text)]">Sản phẩm ({totalCount})</h2>
                            <p className="mt-1 text-xs text-[var(--text-3)]">10 bản ghi/trang · dữ liệu từ product_config.</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <div className="relative w-64">
                                <Input
                                    value={searchQuery}
                                    onChange={(event) => setSearchQuery(event.target.value)}
                                    placeholder="Tìm kiếm sản phẩm..."
                                    className="pl-9 h-[38px] text-[13px] font-medium"
                                />
                                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-3)]">
                                    <Icon name="search" size={15} />
                                </span>
                            </div>
                            <Dropdown value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} options={categoryOptions} placeholder="Tất cả danh mục" className="w-48 h-[38px] text-[13px]" />
                        </div>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="tbl">
                            <thead><tr><th>Sản phẩm</th><th>Thương hiệu</th><th>Danh mục</th><th>Năm</th><th>ID</th><th>Đồng bộ</th><th>Trạng thái</th><th>Hành động</th></tr></thead>
                            <tbody>
                                {loading ? Array.from({ length: PAGE_SIZE }).map((_, row) => (
                                    <tr key={row}>{Array.from({ length: 8 }).map((__, cell) => <td key={cell}><div className="h-4 animate-pulse rounded bg-[var(--surface-3)]" /></td>)}</tr>
                                )) : visibleProducts.length ? visibleProducts.map((item) => (
                                    <tr key={item.product_id}>
                                        <td className="font-bold">{item.product_name}</td>
                                        <td className="muted">{item.brand ?? "—"}</td>
                                        <td>{item.category ? <Badge>{item.category}</Badge> : <span className="muted">—</span>}</td>
                                        <td className="num muted">{item.release_year ?? "—"}</td>
                                        <td><code className="num rounded-md bg-[var(--code-bg)] px-2 py-1 text-xs text-[var(--text-2)]">{item.product_id}</code></td>
                                        <td>
                                            {item.is_synced && item.has_keyword ? (
                                                <Badge variant="success">Đã đồng bộ</Badge>
                                            ) : (
                                                <Badge variant="secondary">Chưa đồng bộ</Badge>
                                            )}
                                        </td>
                                        <td>
                                            <Switch
                                                checked={item.is_active}
                                                onClick={() => void toggleProductActive(item.product_id, item.is_active)}
                                                label={`Trạng thái ${item.product_name}`}
                                            />
                                        </td>
                                        <td className="text-left">
                                            <div className="flex items-center gap-1.5">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    disabled={syncingProductId === item.product_id || (item.is_synced && item.has_keyword)}
                                                    onClick={() => void handleSyncProduct(item.product_id)}
                                                    className="h-8 px-2"
                                                >
                                                    {syncingProductId === item.product_id ? (
                                                        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent mr-1.5" />
                                                    ) : (
                                                        <Icon name="refresh" size={13} className="mr-1.5" />
                                                    )}
                                                    Đồng bộ
                                                </Button>

                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => void handleCrawlProduct(item.product_id, item.product_name)}
                                                    className="h-8 px-2 text-[var(--primary)] hover:text-[var(--primary)]"
                                                >
                                                    <Icon name="search" size={13} className="mr-1.5" />
                                                    Thu thập
                                                </Button>

                                                <Button variant="ghost" size="sm" onClick={() => setSuggestProductId(item.product_id)} className="h-8 px-2">
                                                    <Icon name="spark" size={13} className="mr-1.5 text-amber-500" />
                                                    Gợi ý từ khóa
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                )) : (
                                    <tr><td colSpan={8} className="py-12 text-center text-sm text-[var(--text-3)]">Không có sản phẩm phù hợp.</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                    {!loading && totalCount > 0 && (
                        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--border)] px-4 py-3 text-xs text-[var(--text-3)]">
                            <span>
                                {totalCount} sản phẩm tổng cộng · Hiển thị {pageStart + 1}-{Math.min(pageStart + PAGE_SIZE, totalCount)}
                            </span>
                            <div className="flex items-center gap-2">
                                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Trước</Button>
                                <span className="num text-[var(--text-2)] font-medium">Trang {page}/{totalPages}</span>
                                <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>Sau</Button>
                            </div>
                        </div>
                    )}
                </Card>
            ) : (
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
                    {requestStatuses.map((status) => {
                        const rows = requests[status.value] ?? [];
                        return (
                            <section
                                key={status.value}
                                className={`rounded-[14px] border-2 border-dashed ${draggingId ? "border-[var(--border)]" : "border-transparent"} bg-[var(--surface-2)] p-3.5 transition-colors`}
                                onDragOver={(e) => {
                                    e.preventDefault();
                                    e.dataTransfer.dropEffect = "move";
                                }}
                                onDrop={(e) => void handleDrop(e, status.value)}
                            >
                                <div className="mb-3 flex items-center justify-between gap-3">
                                    <div className="flex items-center gap-2">
                                        <span className={`h-2.5 w-2.5 rounded-full ${status.value === "pending" ? "bg-[#d97706]" : status.value === "processing" ? "bg-[var(--primary)]" : status.value === "approved" ? "bg-[var(--pos)]" : "bg-[var(--neg)]"}`} />
                                        <span className="text-[13.5px] font-bold">{status.label}</span>
                                    </div>
                                    <span className="grid h-6 min-w-6 place-items-center rounded-full bg-[var(--surface)] px-2 text-xs font-extrabold text-[var(--text-2)]">{rows.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {loading ? Array.from({ length: 2 }).map((_, index) => <Card key={index} className="h-24 animate-pulse bg-[var(--surface)] shadow-none" />) : rows.length ? rows.map((request) => (
                                        <button
                                            key={request.request_id}
                                            draggable={request.status === "pending" || request.status === "processing"}
                                            onDragStart={(e) => {
                                                setDraggingId(request.request_id);
                                                e.dataTransfer.effectAllowed = "move";
                                            }}
                                            onDragEnd={() => setDraggingId(null)}
                                            onClick={() => setRequestModal(request)}
                                            className={`w-full rounded-[11px] border border-[var(--border)] bg-[var(--surface)] p-3 text-left shadow-[var(--shadow-sm)] transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)] ${draggingId === request.request_id ? "opacity-50" : ""} ${(request.status === "pending" || request.status === "processing") ? "cursor-grab active:cursor-grabbing" : ""}`}
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

            <Modal open={productModalOpen} title="Thêm sản phẩm" onClose={() => setProductModalOpen(false)} size="3xl">
                <form onSubmit={(event) => { event.preventDefault(); void createProduct(); }} className="space-y-6">
                    {/* Phần 1: Thông tin chung */}
                    <div>
                        <h3 className="mb-3 text-[13px] font-bold text-[var(--primary)] uppercase tracking-wider">Thông tin chung</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Tên model *</label>
                                <Input required value={productForm.product_name} onChange={(event) => setProductForm((form) => ({ ...form, product_name: event.target.value }))} placeholder="vd: iPhone 17 Pro Max" />
                            </div>
                            <div>
                                <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Hãng</label>
                                <Input value={productForm.brand} onChange={(event) => setProductForm((form) => ({ ...form, brand: event.target.value }))} placeholder="vd: Apple" />
                            </div>
                            <div>
                                <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Danh mục *</label>
                                <CategoryCombobox
                                    value={productForm.category}
                                    onChange={(val) => setProductForm((form) => ({ ...form, category: val }))}
                                    options={categoryOptions}
                                />
                            </div>
                            <div>
                                <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Năm phát hành</label>
                                <Input type="number" value={productForm.release_year} onChange={(event) => setProductForm((form) => ({ ...form, release_year: event.target.value }))} placeholder="2026" />
                            </div>
                        </div>
                    </div>

                    {/* Đường phân cách */}
                    <div className="border-t border-[var(--border)]" />

                    {/* Phần 2: Thông số kỹ thuật */}
                    <div>
                        <div className="mb-3 flex items-center justify-between">
                            <h3 className="text-[13px] font-bold text-[var(--primary)] uppercase tracking-wider">Thông số kỹ thuật</h3>
                            {!productForm.category ? null : specs.some((s) => s.isFromTemplate) ? null : (
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setSpecs((prev) => [...prev, { key: "", value: "" }])}
                                    className="h-7 px-2 text-xs"
                                >
                                    <Icon name="plus" size={12} className="mr-1" />
                                    Thêm thông số
                                </Button>
                            )}
                        </div>

                        {!productForm.category ? (
                            <div className="rounded-[10px] border border-dashed border-[var(--border)] bg-[var(--surface-2)] py-6 text-center text-xs text-[var(--text-3)] font-medium">
                                Vui lòng chọn danh mục để điền thông số kỹ thuật.
                            </div>
                        ) : specs.length > 0 ? (
                            specs.some((s) => s.isFromTemplate) ? (
                                // Render theo template dạng Grid 4 cột nằm ngang
                                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 max-h-[220px] overflow-y-auto p-1 ">
                                    {specs.map((spec, idx) => (
                                        <div key={idx} className="flex flex-col gap-1.5">
                                            <label className="text-[12.5px] font-bold text-[var(--text-2)] truncate">
                                                {spec.label} {spec.unit ? `(${spec.unit})` : ""}
                                            </label>
                                            <Input
                                                type={spec.value_type === "number" ? "number" : "text"}
                                                value={spec.value}
                                                onChange={(e) => {
                                                    const next = [...specs];
                                                    next[idx].value = e.target.value;
                                                    setSpecs(next);
                                                }}
                                                placeholder={`Nhập ${spec.label?.toLowerCase() || "giá trị"}...`}
                                                className="h-9 text-xs"
                                            />
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                // Render tự do (Key-Value)
                                <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                                    {specs.map((spec, idx) => (
                                        <div key={idx} className="flex gap-2">
                                            <Input
                                                value={spec.key}
                                                onChange={(e) => {
                                                    const next = [...specs];
                                                    next[idx].key = e.target.value;
                                                    setSpecs(next);
                                                }}
                                                placeholder="Thuộc tính (vd: RAM)"
                                                className="h-9 text-xs w-1/3"
                                            />
                                            <Input
                                                value={spec.value}
                                                onChange={(e) => {
                                                    const next = [...specs];
                                                    next[idx].value = e.target.value;
                                                    setSpecs(next);
                                                }}
                                                placeholder="Giá trị (vd: 12GB)"
                                                className="h-9 text-xs flex-1"
                                            />
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => setSpecs((prev) => prev.filter((_, i) => i !== idx))}
                                                className="h-9 w-9 shrink-0 text-rose-500 hover:text-rose-600 hover:bg-rose-50 p-0"
                                            >
                                                <Icon name="trash" size={14} />
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            )
                        ) : (
                            <div className="rounded-[10px] border border-dashed border-[var(--border)] py-6 text-center text-xs text-[var(--text-3)] font-medium">
                                Danh mục này chưa cấu hình mẫu specs. Bấm "+ Thêm thông số" để nhập tự do.
                                <div className="mt-2">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setSpecs((prev) => [...prev, { key: "", value: "" }])}
                                        className="h-7 px-2 text-xs"
                                    >
                                        <Icon name="plus" size={12} className="mr-1" />
                                        Thêm thông số
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="flex justify-end gap-3 pt-2">
                        <Button type="button" variant="outline" onClick={() => setProductModalOpen(false)}>Hủy</Button>
                        <Button type="submit" disabled={savingProduct || !productForm.product_name.trim()}>{savingProduct ? "Đang lưu..." : "Thêm sản phẩm"}</Button>
                    </div>
                </form>
            </Modal>

            <Modal open={!!requestModal} title="" onClose={() => setRequestModal(null)}>
                {requestModal && (
                    <div className="p-1">
                        {/* Header */}
                        <div className="mb-[26px] flex items-start justify-between border-b border-[var(--border)] pb-5">
                            <h3 className="m-0 text-[16.5px] font-extrabold text-[var(--text)]">Chi tiết phiếu chỉnh sửa</h3>
                        </div>

                        <div className="flex flex-col gap-5">
                            {/* Product Info Block */}
                            <div className="rounded-[11px] bg-[var(--surface-2)] p-[20px]">
                                <div className="mb-1 text-[11.5px] font-bold text-[var(--text-3)]">Sản phẩm</div>
                                <div className="mb-4 text-[15px] font-bold text-[var(--primary)]">{requestModal.product_id}</div>
                                <div className="mb-3 flex items-center gap-2.5">
                                    <Badge variant={statusVariant(requestModal.status)} className="px-2.5 py-0.5 text-xs font-bold rounded-full">{statusLabel(requestModal.status)}</Badge>
                                    <span className="font-mono text-[12.5px] text-[var(--text-3)]">{requestModal.request_id}</span>
                                </div>
                                <div className="text-[12.5px] font-medium text-[var(--text-3)]">{formatDate(requestModal.created_at)}</div>
                            </div>

                            {requestModal.proposed_description && (
                                <div>
                                    <div className="mb-2 text-[12px] font-bold text-[var(--text-2)]">Mô tả đề xuất</div>
                                    <div className="rounded-[10px] bg-[var(--surface-2)] p-[14px] text-[13px] text-[var(--text)] font-medium leading-relaxed">{requestModal.proposed_description}</div>
                                </div>
                            )}

                            {(requestModal.proposed_official_url || requestModal.proposed_image_url) && (
                                <div className="grid grid-cols-2 gap-4">
                                    {requestModal.proposed_official_url && (
                                        <div>
                                            <div className="mb-2 text-[12px] font-bold text-[var(--text-2)]">Official URL</div>
                                            <div className="break-all rounded-[10px] bg-[var(--surface-2)] p-3 font-mono text-[11.5px] text-[var(--primary)]">{requestModal.proposed_official_url}</div>
                                        </div>
                                    )}
                                    {requestModal.proposed_image_url && (
                                        <div>
                                            <div className="mb-2 text-[12px] font-bold text-[var(--text-2)]">Image URL</div>
                                            <div className="break-all rounded-[10px] bg-[var(--surface-2)] p-3 font-mono text-[11.5px] text-[var(--primary)]">{requestModal.proposed_image_url}</div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {requestModal.proposed_specs && Object.keys(requestModal.proposed_specs).length > 0 && (
                                <div>
                                    <div className="mb-2 text-[13px] font-bold text-[var(--text-2)]">Thông số đề xuất</div>
                                    <pre className="block rounded-[10px] bg-[var(--surface-2)] px-[18px] py-[16px] font-mono text-[13px] leading-[1.7] text-[var(--text)] whitespace-pre-wrap break-words">
                                        {JSON.stringify(requestModal.proposed_specs, null, 2)}
                                    </pre>
                                </div>
                            )}

                            {requestModal.status === "pending" && (
                                <div className="mt-2 flex justify-end gap-3">
                                    <Button
                                        disabled={reviewingId === requestModal.request_id}
                                        onClick={() => void reviewRequest(requestModal.request_id, "processing")}
                                        className="bg-[var(--surface)] text-[var(--text)] hover:bg-[var(--surface-3)] border border-[var(--border)] rounded-[10px] px-[22px] py-[22px] text-[14.5px] font-bold shadow-sm transition-all mr-auto"
                                    >
                                        Chuyển sang Xử lý
                                    </Button>
                                    <Button
                                        disabled={reviewingId === requestModal.request_id}
                                        onClick={() => void reviewRequest(requestModal.request_id, "reject")}
                                        className="bg-[#f43f5e] hover:bg-[#e11d48] text-white rounded-[10px] px-[22px] py-[22px] text-[14.5px] font-bold shadow-sm transition-all"
                                    >
                                        Từ chối
                                    </Button>
                                    <Button
                                        disabled={reviewingId === requestModal.request_id}
                                        onClick={() => void reviewRequest(requestModal.request_id, "approve")}
                                        className="bg-[#10b981] hover:bg-[#059669] text-white rounded-[10px] px-[22px] py-[22px] text-[14.5px] font-bold shadow-sm transition-all"
                                    >
                                        Duyệt
                                    </Button>
                                </div>
                            )}
                            {requestModal.status === "processing" && (
                                <div className="mt-2 flex justify-end gap-3">
                                    <Button
                                        disabled={reviewingId === requestModal.request_id}
                                        onClick={() => void reviewRequest(requestModal.request_id, "reject")}
                                        className="bg-[#f43f5e] hover:bg-[#e11d48] text-white rounded-[10px] px-[22px] py-[22px] text-[14.5px] font-bold shadow-sm transition-all"
                                    >
                                        Từ chối
                                    </Button>
                                    <Button
                                        disabled={reviewingId === requestModal.request_id}
                                        onClick={() => void reviewRequest(requestModal.request_id, "approve")}
                                        className="bg-[#10b981] hover:bg-[#059669] text-white rounded-[10px] px-[22px] py-[22px] text-[14.5px] font-bold shadow-sm transition-all"
                                    >
                                        Duyệt
                                    </Button>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </Modal>

            <KeywordSuggestionModal
                open={suggestProductId !== null}
                productId={suggestProductId}
                onClose={() => setSuggestProductId(null)}
            />

            <CrawlProgress
                open={crawlProgressOpen}
                taskId={activeTaskId}
                productName={crawlProductName}
                onClose={() => {
                    setCrawlProgressOpen(false);
                    setActiveTaskId(null);
                }}
                onComplete={() => {
                    void loadProducts(page, true);
                }}
            />

            {quotaConfirmProduct && (
                <Modal
                    open={quotaConfirmProduct !== null}
                    title="Cảnh báo Quota API"
                    onClose={() => setQuotaConfirmProduct(null)}
                >
                    <div className="space-y-4">
                        <div className="text-sm font-medium text-[var(--text-2)] leading-relaxed">
                            Hệ thống đã hết Quota YouTube API trong ngày hôm nay. Bạn có muốn sử dụng chế độ tìm kiếm và thu thập dự phòng bằng <strong>yt-dlp</strong> (tiêu tốn 0 quota) cho sản phẩm <strong>{quotaConfirmProduct.name}</strong> không?
                        </div>
                        <div className="flex justify-end gap-3 pt-2">
                            <Button variant="outline" onClick={() => setQuotaConfirmProduct(null)}>Hủy</Button>
                            <Button
                                onClick={() => void handleCrawlProduct(quotaConfirmProduct.id, quotaConfirmProduct.name, true)}
                            >
                                Đồng ý sử dụng yt-dlp
                            </Button>
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
}
