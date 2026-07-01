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
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";
import { KeywordSuggestionModal } from "@/components/admin/KeywordSuggestionModal";
import { CrawlProgress } from "@/components/admin/CrawlProgress";

const PAGE_SIZE = 10;
const requestStatuses = [
    { value: "pending", label: "Đang chờ", variant: "warning" },
    { value: "processing", label: "Đang xử lý", variant: "default" },
    { value: "approved", label: "Đã duyệt", variant: "success" },
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
    const [runningCrawls, setRunningCrawls] = useState<Record<string, { taskId: string; progress: number; status: string; message: string }>>({});
    const crawlPollRefs = useRef<Record<string, NodeJS.Timeout>>({});

    // New states for detail change requests modal redesign
    const [fullProductList, setFullProductList] = useState<ProductConfigItem[]>([]);
    const [modalStatus, setModalStatus] = useState<"pending" | "processing" | "approved" | "rejected">("pending");
    const [modalReviewNote, setModalReviewNote] = useState("");

    // New states for editing product
    const [productEditModalOpen, setProductEditModalOpen] = useState(false);
    const [editProductId, setEditProductId] = useState<string | null>(null);
    const [loadingEditProduct, setLoadingEditProduct] = useState(false);
    const [editForm, setEditForm] = useState({
        product_name: "",
        brand: "",
        category: "",
        release_year: "",
        is_active: true,
        description: "",
        official_url: "",
        image_url: "",
    });
    const [editSpecs, setEditSpecs] = useState<{
        key: string;
        label?: string;
        value: string;
        value_type?: string;
        unit?: string | null;
        isFromTemplate?: boolean;
    }[]>([]);

    useEffect(() => {
        if (requestModal) {
            setModalStatus(requestModal.status);
            setModalReviewNote("");
        }
    }, [requestModal]);

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
            setFullProductList(fullProducts);

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

    const handleOpenEditModal = async (productId: string) => {
        setLoadingEditProduct(true);
        const basicProd = products.find(p => p.product_id === productId);
        if (basicProd) {
            setEditForm({
                product_name: basicProd.product_name || "",
                brand: basicProd.brand || "",
                category: basicProd.category || "",
                release_year: basicProd.release_year ? String(basicProd.release_year) : "",
                is_active: basicProd.is_active,
                description: "",
                official_url: "",
                image_url: "",
            });
            const categoryTemplates = templates.filter(
                (t) => t.category.toLowerCase() === (basicProd.category || "").toLowerCase()
            );
            if (categoryTemplates.length > 0) {
                setEditSpecs(
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
                setEditSpecs([]);
            }
        }
        setProductEditModalOpen(true);
        setEditProductId(productId);

        try {
            const detailProd = await api.admin.products.get(productId);
            setEditForm({
                product_name: detailProd.product_name || "",
                brand: detailProd.brand || "",
                category: detailProd.category || "",
                release_year: detailProd.release_year ? String(detailProd.release_year) : "",
                is_active: detailProd.is_active,
                description: detailProd.description || "",
                official_url: detailProd.official_url || "",
                image_url: detailProd.image_url || "",
            });

            const categoryTemplates = templates.filter(
                (t) => t.category.toLowerCase() === (detailProd.category || "").toLowerCase()
            );

            const existingSpecsObj = detailProd.specs || {};

            if (categoryTemplates.length > 0) {
                setEditSpecs(
                    categoryTemplates.map((t) => {
                        const val = existingSpecsObj[t.spec_key];
                        let displayVal = "";
                        if (val !== undefined && val !== null) {
                            displayVal = String(val);
                        }
                        return {
                            key: t.spec_key,
                            label: t.display_label,
                            value: displayVal,
                            value_type: t.value_type,
                            unit: t.unit,
                            isFromTemplate: true
                        };
                    })
                );
            } else {
                const customSpecs = Object.entries(existingSpecsObj).map(([k, v]) => ({
                    key: k,
                    value: String(v),
                    isFromTemplate: false
                }));
                setEditSpecs(customSpecs);
            }
        } catch (err) {
            console.error("Failed to load product details:", err);
        } finally {
            setLoadingEditProduct(false);
        }
    };

    const handleEditCategoryChange = (newCat: string) => {
        setEditForm(prev => ({ ...prev, category: newCat }));
        const categoryTemplates = templates.filter(
            (t) => t.category.toLowerCase() === newCat.toLowerCase()
        );
        if (categoryTemplates.length > 0) {
            setEditSpecs(
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
            setEditSpecs([]);
        }
    };

    async function saveProductEdit() {
        if (!editProductId || !editForm.product_name.trim()) return;
        setSavingProduct(true);
        try {
            const specsObj: Record<string, any> = {};
            editSpecs.forEach((item) => {
                const k = item.key.trim();
                const v = item.value.trim();
                if (k && v) {
                    if (v.toLowerCase() === "true") specsObj[k] = true;
                    else if (v.toLowerCase() === "false") specsObj[k] = false;
                    else if (!isNaN(Number(v)) && v !== "") specsObj[k] = Number(v);
                    else specsObj[k] = v;
                }
            });

            await api.admin.products.update(editProductId, {
                product_name: editForm.product_name.trim(),
                brand: editForm.brand.trim() || undefined,
                category: editForm.category.trim() || undefined,
                release_year: editForm.release_year ? Number(editForm.release_year) : undefined,
                is_active: editForm.is_active,
                specs: specsObj,
                description: editForm.description.trim() || "",
                official_url: editForm.official_url.trim() || "",
                image_url: editForm.image_url.trim() || "",
            });

            setProductEditModalOpen(false);
            setEditProductId(null);
            await load();
            await loadProducts(page, true);
        } catch (err: unknown) {
            const e = err as { detail?: string };
            setError(e?.detail ?? "Không thể lưu thông tin chỉnh sửa sản phẩm.");
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

    const startCrawlPolling = useCallback((productId: string, taskId: string) => {
        if (crawlPollRefs.current[productId]) {
            clearInterval(crawlPollRefs.current[productId]);
        }
        const poll = async () => {
            try {
                const res = await api.admin.products.crawlTaskStatus(taskId);
                setRunningCrawls(prev => ({
                    ...prev,
                    [productId]: { taskId, progress: res.progress, status: res.status, message: res.message }
                }));
                if (res.status === "success" || res.status === "failed") {
                    clearInterval(crawlPollRefs.current[productId]);
                    delete crawlPollRefs.current[productId];
                    if (res.status === "success") {
                        void loadProducts(page, true);
                    }
                    setTimeout(() => {
                        setRunningCrawls(prev => {
                            const next = { ...prev };
                            delete next[productId];
                            return next;
                        });
                    }, 5000);
                }
            } catch (err) {
                console.error("Poll crawl status error:", err);
            }
        };
        void poll();
        crawlPollRefs.current[productId] = setInterval(poll, 3000);
    }, [loadProducts, page]);

    const [crawlProductId, setCrawlProductId] = useState<string | null>(null);

    async function handleCrawlProduct(productId: string, productName: string, useYtdlp = false) {
        try {
            setQuotaConfirmProduct(null);
            const res = await api.admin.products.crawl(productId, useYtdlp);
            if (res.status === "quota_exhausted") {
                setQuotaConfirmProduct({ id: productId, name: productName });
            } else if (res.task_id) {
                setCrawlProductId(productId);
                setCrawlProductName(productName);
                setActiveTaskId(res.task_id);
                setCrawlProgressOpen(true);
                startCrawlPolling(productId, res.task_id);
            }
        } catch (err: any) {
            console.error(err);
            alert(err?.detail ?? "Không thể bắt đầu thu thập dữ liệu.");
        }
    }

    async function reviewRequest(requestId: string, action: "approve" | "reject" | "processing", reviewNote?: string) {
        setReviewingId(requestId);
        try {
            await api.admin.products.reviewDetailRequest(requestId, action, reviewNote);
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

    const getProductNameById = (id: string) => {
        const prod = fullProductList.find(p => p.product_id === id);
        return prod ? prod.product_name : id;
    };

    const getRequestTitle = (req: ProductDetailChangeRequestItem) => {
        if (req.proposed_specs && Object.keys(req.proposed_specs).length > 0) {
            const keys = Object.keys(req.proposed_specs);
            const fallbackInfo: Record<string, string> = {
                screen_technology: "công nghệ màn hình",
                screen_size_inches: "kích thước màn hình",
                ram_gb: "dung lượng RAM",
                storage_gb: "bộ nhớ trong",
                battery_mah: "dung lượng pin",
                chipset: "vi xử lý",
                generation: "thế hệ",
                release_date: "ngày ra mắt",
                model_year: "năm model",
                processor: "bộ vi xử lý (CPU)",
                graphics: "card đồ họa (gpu)",
                battery_hours: "thời lượng pin",
                connection: "kết nối",
                connector: "cổng sạc",
                noise_cancellation: "chống ồn chủ động (ANC)",
                screen_size: "kích thước màn hình",
                resolution: "độ phân giải",
                cpu: "bộ vi xử lý (CPU)",
                ram: "bộ nhớ trong (RAM)",
                rom: "dung lượng lưu trữ (ROM)",
                battery: "dung lượng pin",
                os: "hệ điều hành",
                weight: "trọng lượng",
                color: "màu sắc",
                camera: "camera",
                gpu: "card đồ họa (GPU)",
                screen_type: "công nghệ màn hình",
                release_year: "năm ra mắt",
            };
            const labels = keys.map(key => {
                const template = templates.find(t => t.spec_key === key);
                if (template) return template.display_label.toLowerCase();
                return fallbackInfo[key] || key;
            });
            return `Cập nhật thông số (${labels.join(", ")})`;
        }
        if (req.proposed_description) return "Cập nhật mô tả sản phẩm";
        if (req.proposed_official_url) return "Cập nhật đường dẫn chính thức";
        if (req.proposed_image_url) return "Cập nhật ảnh sản phẩm";
        return "Cập nhật thông tin sản phẩm";
    };

    const renderFriendlyContent = (req: ProductDetailChangeRequestItem) => {
        const specs = req.proposed_specs;
        const desc = req.proposed_description;
        const officialUrl = req.proposed_official_url;
        const imageUrl = req.proposed_image_url;

        return (
            <div className="rounded-[12px] bg-[#f3f0ff] p-4 text-[#5c3e9b] space-y-3 font-medium">
                {specs && Object.keys(specs).length > 0 && (
                    <div className="space-y-1.5 text-[13px]">
                        {Object.entries(specs).map(([key, val]) => {
                            const template = templates.find(t => t.spec_key === key);
                            const label = template ? template.display_label : key;
                            const unit = template && template.unit ? ` (${template.unit})` : "";
                            let displayValue = String(val);
                            if (val === true) displayValue = "Có";
                            else if (val === false) displayValue = "Không";
                            return (
                                <div key={key} className="flex justify-between border-b border-purple-100 py-1 last:border-0">
                                    <span>{label}{unit}:</span>
                                    <span className="font-bold text-violet-950">{displayValue}</span>
                                </div>
                            );
                        })}
                    </div>
                )}
                {desc && (
                    <div className="text-[13px] leading-relaxed">
                        <span className="block text-[11px] font-bold text-purple-700 uppercase tracking-wider mb-1">Mô tả sản phẩm</span>
                        <p className="m-0 font-semibold text-violet-950">{desc}</p>
                    </div>
                )}
                {officialUrl && (
                    <div className="text-[13px]">
                        <span className="block text-[11px] font-bold text-purple-700 uppercase tracking-wider mb-1">Trang web chính thức</span>
                        <a href={officialUrl} target="_blank" rel="noreferrer" className="underline font-bold text-violet-950 hover:text-violet-850 break-all">{officialUrl}</a>
                    </div>
                )}
                {imageUrl && (
                    <div className="text-[13px] space-y-1">
                        <span className="block text-[11px] font-bold text-purple-700 uppercase tracking-wider">Ảnh sản phẩm</span>
                        <a href={imageUrl} target="_blank" rel="noreferrer" className="underline font-bold text-violet-950 hover:text-violet-850 break-all block">{imageUrl}</a>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={imageUrl} alt="Đề xuất" className="max-h-24 rounded-lg object-contain border border-purple-200 mt-2" />
                    </div>
                )}
            </div>
        );
    };

    const handleSaveRequestChanges = () => {
        if (!requestModal) return;
        let action: "approve" | "reject" | "processing";
        if (modalStatus === "approved") action = "approve";
        else if (modalStatus === "rejected") action = "reject";
        else if (modalStatus === "processing") action = "processing";
        else {
            setRequestModal(null);
            return;
        }
        void reviewRequest(requestModal.request_id, action, modalReviewNote);
    };

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
                {tab === "catalog" && (
                    <Button onClick={() => setProductModalOpen(true)}>
                        <Icon name="plus" size={16} className="mr-1.5" />
                        Thêm sản phẩm
                    </Button>
                )}
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
                                    <tr 
                                        key={item.product_id}
                                        onClick={() => void handleOpenEditModal(item.product_id)}
                                        className="hover:bg-[var(--surface-3)] transition-colors cursor-pointer"
                                    >
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
                                        <td onClick={(e) => e.stopPropagation()}>
                                            <Switch
                                                checked={item.is_active}
                                                onClick={() => {
                                                    void toggleProductActive(item.product_id, item.is_active);
                                                }}
                                                label={`Trạng thái ${item.product_name}`}
                                            />
                                        </td>
                                        <td onClick={(e) => e.stopPropagation()} className="text-left">
                                            {runningCrawls[item.product_id] && !crawlProgressOpen ? (
                                                <div
                                                    className="flex items-center gap-2 cursor-pointer rounded-lg px-2 py-1.5 hover:bg-[var(--surface-3)] transition-colors"
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setCrawlProductId(item.product_id);
                                                        setCrawlProductName(item.product_name);
                                                        setActiveTaskId(runningCrawls[item.product_id].taskId);
                                                        setCrawlProgressOpen(true);
                                                    }}
                                                >
                                                    {runningCrawls[item.product_id].status === "success" ? (
                                                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white text-[9px]">✓</span>
                                                    ) : runningCrawls[item.product_id].status === "failed" ? (
                                                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-rose-500 text-white text-[9px] font-bold">!</span>
                                                    ) : (
                                                        <div className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-[var(--primary)] border-t-transparent" />
                                                    )}
                                                    <div className="flex-1 min-w-0">
                                                        <div className="w-full bg-[var(--surface-3)] h-1.5 rounded-full overflow-hidden">
                                                            <div
                                                                className={`h-full rounded-full transition-all duration-500 ${
                                                                    runningCrawls[item.product_id].status === "success" ? "bg-emerald-500"
                                                                    : runningCrawls[item.product_id].status === "failed" ? "bg-rose-500"
                                                                    : "bg-[var(--primary)]"
                                                                }`}
                                                                style={{ width: `${runningCrawls[item.product_id].progress}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-[10.5px] font-semibold text-[var(--text-3)] mt-0.5 block truncate">
                                                            {runningCrawls[item.product_id].progress}% · {runningCrawls[item.product_id].message}
                                                        </span>
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-1">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            void handleOpenEditModal(item.product_id);
                                                        }}
                                                        className="h-8 px-2 font-medium"
                                                    >
                                                        <Icon name="edit" size={13} className="mr-1 text-[var(--primary)]" />
                                                        Sửa
                                                    </Button>

                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            void handleCrawlProduct(item.product_id, item.product_name);
                                                        }}
                                                        className="h-8 px-2 font-medium text-[var(--primary)] hover:text-[var(--primary)]"
                                                    >
                                                        <Icon name="play" size={13} className="mr-1 text-emerald-500" />
                                                        Thu thập
                                                    </Button>

                                                    {!(item.is_synced && item.has_keyword) && (
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            disabled={syncingProductId === item.product_id}
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                void handleSyncProduct(item.product_id);
                                                            }}
                                                            className="h-8 px-2 font-medium"
                                                        >
                                                            {syncingProductId === item.product_id ? (
                                                                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent mr-1.5" />
                                                            ) : (
                                                                <Icon name="refresh" size={13} className="mr-1 text-amber-500" />
                                                            )}
                                                            Đồng bộ
                                                        </Button>
                                                    )}
                                                </div>
                                            )}
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
                                            <div className="mb-1 truncate text-[11.5px] font-bold text-[var(--primary)]">
                                                {request.product_name || request.product_id}
                                            </div>
                                            <div className="line-clamp-2 text-[13.5px] font-bold leading-snug text-[var(--text)]">
                                                {getRequestTitle(request)}
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

            <Modal 
                open={productEditModalOpen} 
                title={
                    <div className="flex items-center justify-between w-full pr-8">
                        <div>
                            <h3 className="m-0 text-[18px] font-extrabold text-[var(--text)]">Chỉnh sửa thông tin sản phẩm</h3>
                            <div className="text-xs text-[var(--text-3)] font-medium mt-1">
                                Mã: <code className="num rounded bg-[var(--code-bg)] px-1.5 py-0.5 text-xs text-[var(--text-2)]">{editProductId}</code>
                            </div>
                        </div>
                        {editProductId && (
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                disabled={syncingProductId === editProductId}
                                onClick={() => void handleSyncProduct(editProductId!)}
                                className="h-8 px-3 font-semibold text-xs border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-700 flex items-center gap-1.5"
                            >
                                {syncingProductId === editProductId ? (
                                    <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-amber-600 border-t-transparent" />
                                ) : (
                                    <Icon name="refresh" size={13} className="text-amber-500" />
                                )}
                                Đồng bộ ngay
                            </Button>
                        )}
                    </div>
                } 
                onClose={() => { setProductEditModalOpen(false); setEditProductId(null); }} 
                size="3xl"
            >
                {loadingEditProduct ? (
                    <div className="py-12 flex flex-col items-center justify-center gap-3">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--primary)] border-t-transparent" />
                        <span className="text-sm font-medium text-[var(--text-3)]">Đang tải dữ liệu chi tiết sản phẩm...</span>
                    </div>
                ) : (
                    <form onSubmit={(event) => { event.preventDefault(); void saveProductEdit(); }} className="space-y-6">
                        {/* Phần 1: Thông tin chung */}
                        <div>
                            <h3 className="mb-3 text-[13px] font-bold text-[var(--primary)] uppercase tracking-wider">Thông tin chung</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Tên model *</label>
                                    <Input required value={editForm.product_name} onChange={(event) => setEditForm((form) => ({ ...form, product_name: event.target.value }))} placeholder="vd: iPhone 17 Pro Max" />
                                </div>
                                <div>
                                    <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Hãng</label>
                                    <Input value={editForm.brand} onChange={(event) => setEditForm((form) => ({ ...form, brand: event.target.value }))} placeholder="vd: Apple" />
                                </div>
                                <div>
                                    <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Danh mục *</label>
                                    <CategoryCombobox
                                        value={editForm.category}
                                        onChange={handleEditCategoryChange}
                                        options={categoryOptions}
                                    />
                                </div>
                                <div>
                                    <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Năm phát hành</label>
                                    <Input type="number" value={editForm.release_year} onChange={(event) => setEditForm((form) => ({ ...form, release_year: event.target.value }))} placeholder="2026" />
                                </div>
                            </div>
                        </div>

                        {/* Đường phân cách */}
                        <div className="border-t border-[var(--border)]" />

                        {/* Phần 2: Thông tin chi tiết */}
                        <div>
                            <h3 className="mb-3 text-[13px] font-bold text-[var(--primary)] uppercase tracking-wider">Thông tin chi tiết</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Mô tả sản phẩm</label>
                                    <Textarea 
                                        value={editForm.description} 
                                        onChange={(event) => setEditForm((form) => ({ ...form, description: event.target.value }))} 
                                        placeholder="Nhập mô tả sản phẩm..." 
                                        className="min-h-[80px]"
                                    />
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Trang web chính thức</label>
                                        <Input value={editForm.official_url} onChange={(event) => setEditForm((form) => ({ ...form, official_url: event.target.value }))} placeholder="https://example.com/product" />
                                    </div>
                                    <div>
                                        <label className="mb-1.5 block text-[12.5px] font-bold text-[var(--text-2)]">Ảnh sản phẩm (URL)</label>
                                        <Input value={editForm.image_url} onChange={(event) => setEditForm((form) => ({ ...form, image_url: event.target.value }))} placeholder="https://example.com/product-image.jpg" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Đường phân cách */}
                        <div className="border-t border-[var(--border)]" />

                        {/* Phần 3: Thông số kỹ thuật */}
                        <div>
                            <div className="mb-3 flex items-center justify-between">
                                <h3 className="text-[13px] font-bold text-[var(--primary)] uppercase tracking-wider">Thông số kỹ thuật</h3>
                                {!editForm.category ? null : editSpecs.some((s) => s.isFromTemplate) ? null : (
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setEditSpecs((prev) => [...prev, { key: "", value: "" }])}
                                        className="h-7 px-2 text-xs"
                                    >
                                        <Icon name="plus" size={12} className="mr-1" />
                                        Thêm thông số
                                    </Button>
                                )}
                            </div>

                            {!editForm.category ? (
                                <div className="rounded-[10px] border border-dashed border-[var(--border)] bg-[var(--surface-2)] py-6 text-center text-xs text-[var(--text-3)] font-medium">
                                    Vui lòng chọn danh mục để điền thông số kỹ thuật.
                                </div>
                            ) : editSpecs.length > 0 ? (
                                editSpecs.some((s) => s.isFromTemplate) ? (
                                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 max-h-[220px] overflow-y-auto p-1">
                                        {editSpecs.map((spec, idx) => (
                                            <div key={idx} className="flex flex-col gap-1.5">
                                                <label className="text-[12.5px] font-bold text-[var(--text-2)] truncate">
                                                    {spec.label} {spec.unit ? `(${spec.unit})` : ""}
                                                </label>
                                                <Input
                                                    type={spec.value_type === "number" ? "number" : "text"}
                                                    value={spec.value}
                                                    onChange={(e) => {
                                                        const next = [...editSpecs];
                                                        next[idx].value = e.target.value;
                                                        setEditSpecs(next);
                                                    }}
                                                    placeholder={`Nhập ${spec.label?.toLowerCase() || "giá trị"}...`}
                                                    className="h-9 text-xs"
                                                />
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
                                        {editSpecs.map((spec, idx) => (
                                            <div key={idx} className="flex gap-2">
                                                <Input
                                                    value={spec.key}
                                                    onChange={(e) => {
                                                        const next = [...editSpecs];
                                                        next[idx].key = e.target.value;
                                                        setEditSpecs(next);
                                                    }}
                                                    placeholder="Thuộc tính (vd: RAM)"
                                                    className="h-9 text-xs w-1/3"
                                                />
                                                <Input
                                                    value={spec.value}
                                                    onChange={(e) => {
                                                        const next = [...editSpecs];
                                                        next[idx].value = e.target.value;
                                                        setEditSpecs(next);
                                                    }}
                                                    placeholder="Giá trị (vd: 12GB)"
                                                    className="h-9 text-xs flex-1"
                                                />
                                                <Button
                                                    type="button"
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => setEditSpecs((prev) => prev.filter((_, i) => i !== idx))}
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
                                            onClick={() => setEditSpecs((prev) => [...prev, { key: "", value: "" }])}
                                            className="h-7 px-2 text-xs"
                                        >
                                            <Icon name="plus" size={12} className="mr-1" />
                                            Thêm thông số
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="flex justify-between items-center pt-2">
                            <div className="flex items-center gap-2">
                                <label className="text-[12.5px] font-bold text-[var(--text-2)]">Kích hoạt sản phẩm</label>
                                <Switch
                                    checked={editForm.is_active}
                                    onClick={() => setEditForm(prev => ({ ...prev, is_active: !prev.is_active }))}
                                    label="Kích hoạt"
                                />
                            </div>
                            <div className="flex gap-3">
                                <Button type="button" variant="outline" onClick={() => { setProductEditModalOpen(false); setEditProductId(null); }}>Hủy</Button>
                                <Button type="submit" disabled={savingProduct || !editForm.product_name.trim()}>{savingProduct ? "Đang lưu..." : "Lưu thay đổi"}</Button>
                            </div>
                        </div>
                    </form>
                )}
            </Modal>

            <Modal
                open={!!requestModal}
                title={requestModal ? (
                    <div>
                        <h3 className="m-0 text-[18px] font-extrabold text-[var(--text)]">Chi tiết phiếu chỉnh sửa</h3>
                        <div className="text-xs text-[var(--text-3)] font-medium mt-1">
                            #{requestModal.request_id.substring(0, 8)} · Gửi ngày {formatDate(requestModal.created_at)}
                        </div>
                    </div>
                ) : ""}
                onClose={() => setRequestModal(null)}
            >
                {requestModal && (
                    <div className="p-1">
                        <div className="flex flex-col gap-5">
                            {/* Khung thông tin Người gửi & Sản phẩm */}
                            <div className="rounded-[16px] bg-[var(--surface-2)] p-4 flex justify-between items-center shadow-sm">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-violet-600 text-white flex items-center justify-center font-bold text-[15px]">
                                        {requestModal.submitted_by.substring(0, 2).toUpperCase()}
                                    </div>
                                    <div>
                                        <div className="text-[13.5px] font-bold text-[var(--text-1)]">{requestModal.submitted_by}</div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="text-[10px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-0.5">Sản phẩm</div>
                                    <div className="text-[14.5px] font-extrabold text-violet-600">
                                        {getProductNameById(requestModal.product_id)}
                                    </div>
                                </div>
                            </div>

                            {/* Tiêu đề chỉnh sửa */}
                            <div>
                                <div className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-1.5">Tiêu đề chỉnh sửa</div>
                                <div className="text-[15px] font-bold text-[var(--text)]">
                                    {getRequestTitle(requestModal)}
                                </div>
                            </div>

                            {/* Nội dung chỉnh sửa */}
                            <div>
                                <div className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-1.5">Nội dung chỉnh sửa</div>
                                {renderFriendlyContent(requestModal)}
                            </div>

                            {/* Trạng thái & Người xử lý */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-1.5 block">Trạng thái</label>
                                    <div className="h-10 flex items-center px-3 rounded-[12px] border border-[var(--border)] bg-[var(--surface-3)] font-semibold text-[13.5px]">
                                        <span className={`w-2.5 h-2.5 rounded-full mr-2 ${requestModal.status === "approved" ? "bg-[var(--pos)]" :
                                                requestModal.status === "rejected" ? "bg-[var(--neg)]" :
                                                    requestModal.status === "processing" ? "bg-[var(--primary)]" : "bg-[#d97706]"
                                            }`} />
                                        {statusLabel(requestModal.status)}
                                    </div>
                                </div>
                                <div>
                                    <label className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-1.5 block">Người xử lý</label>
                                    <div className="h-10 flex items-center px-3 rounded-[12px] border border-[var(--border)] bg-[var(--surface-3)] font-medium text-[13px] text-[var(--text-3)] truncate">
                                        {requestModal.reviewed_by || "Chưa phân công"}
                                    </div>
                                </div>
                            </div>

                            {/* Ghi chú duyệt / lý do từ chối */}
                            {(requestModal.status === "pending" || requestModal.status === "processing") ? (
                                <div className="space-y-1.5 animate-in fade-in slide-in-from-top-2 duration-200">
                                    <label className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider block">Ghi chú duyệt / Lý do từ chối</label>
                                    <Textarea
                                        value={modalReviewNote}
                                        onChange={(e) => setModalReviewNote(e.target.value)}
                                        placeholder="Nhập ghi chú hoặc lý do từ chối..."
                                        className="min-h-[72px] text-[13px] rounded-[10px]"
                                    />
                                </div>
                            ) : requestModal.review_note ? (
                                <div className="space-y-1.5">
                                    <label className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider block">Ghi chú duyệt / Lý do từ chối</label>
                                    <div className="rounded-[10px] bg-[var(--surface-3)] p-3 text-[13px] font-medium text-[var(--text-2)]">
                                        {requestModal.review_note}
                                    </div>
                                </div>
                            ) : null}

                            {/* Nút bấm Footer */}
                            {(requestModal.status === "pending" || requestModal.status === "processing") && (
                                <div className="mt-2 flex justify-end gap-3 pt-4 border-t border-[var(--border)]">
                                    {requestModal.status === "pending" ? (
                                        <>
                                            <Button
                                                variant="destructive"
                                                disabled={reviewingId === requestModal.request_id}
                                                onClick={() => void reviewRequest(requestModal.request_id, "reject", modalReviewNote)}
                                                className="rounded-[12px] px-5 py-2.5 h-10 text-[13.5px] font-bold shadow-sm transition-all"
                                            >
                                                Từ chối
                                            </Button>
                                            <Button
                                                variant="default"
                                                disabled={reviewingId === requestModal.request_id}
                                                onClick={() => void reviewRequest(requestModal.request_id, "processing", modalReviewNote)}
                                                className="bg-violet-600 hover:bg-violet-700 text-white rounded-[12px] px-5 py-2.5 h-10 text-[13.5px] font-bold shadow-sm transition-all flex items-center gap-1.5"
                                            >
                                                {reviewingId === requestModal.request_id ? (
                                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                                ) : (
                                                    <Icon name="check" size={15} />
                                                )}
                                                Tiếp nhận
                                            </Button>
                                        </>
                                    ) : (
                                        <>
                                            <Button
                                                variant="destructive"
                                                disabled={reviewingId === requestModal.request_id}
                                                onClick={() => void reviewRequest(requestModal.request_id, "reject", modalReviewNote)}
                                                className="rounded-[12px] px-5 py-2.5 h-10 text-[13.5px] font-bold shadow-sm transition-all"
                                            >
                                                Từ chối
                                            </Button>
                                            <Button
                                                variant="success"
                                                disabled={reviewingId === requestModal.request_id}
                                                onClick={() => void reviewRequest(requestModal.request_id, "approve", modalReviewNote)}
                                                className="rounded-[12px] px-5 py-2.5 h-10 text-[13.5px] font-bold shadow-sm transition-all flex items-center gap-1.5"
                                            >
                                                {reviewingId === requestModal.request_id ? (
                                                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                                                ) : (
                                                    <Icon name="check" size={15} />
                                                )}
                                                Duyệt
                                            </Button>
                                        </>
                                    )}
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
