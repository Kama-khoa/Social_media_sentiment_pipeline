"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type { ProductDetailChangeRequestItem } from "@/lib/types";
import { Icon } from "@/components/shared/Icon";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/admin/Modal";

const statusMapping = {
  pending: { label: "Đang chờ", variant: "warning" as const },
  processing: { label: "Đang xử lý", variant: "brand" as const },
  approved: { label: "Đã duyệt", variant: "success" as const },
  rejected: { label: "Từ chối", variant: "destructive" as const },
} as const;

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("vi-VN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// Map common spec keys to Vietnamese labels and units
const COMMON_SPEC_LABELS: Record<string, { label: string; unit?: string }> = {
  screen_technology: { label: "Công nghệ màn hình" },
  screen_size_inches: { label: "Kích thước màn hình", unit: "inch" },
  ram_gb: { label: "Dung lượng RAM", unit: "GB" },
  storage_gb: { label: "Bộ nhớ trong", unit: "GB" },
  battery_mah: { label: "Dung lượng pin", unit: "mAh" },
  chipset: { label: "Vi xử lý (Chipset)" },
  generation: { label: "Thế hệ" },
  release_date: { label: "Ngày ra mắt" },
  model_year: { label: "Năm model" },
  processor: { label: "Bộ vi xử lý (CPU)" },
  graphics: { label: "Card đồ họa (GPU)" },
  battery_hours: { label: "Thời lượng pin", unit: "giờ" },
  connection: { label: "Kết nối" },
  connector: { label: "Cổng sạc" },
  noise_cancellation: { label: "Chống ồn chủ động (ANC)" },
  // Fallbacks
  screen_size: { label: "Kích thước màn hình", unit: "inch" },
  resolution: { label: "Độ phân giải" },
  cpu: { label: "Bộ vi xử lý (CPU)" },
  ram: { label: "Bộ nhớ trong (RAM)", unit: "GB" },
  rom: { label: "Dung lượng lưu trữ (ROM)", unit: "GB" },
  battery: { label: "Dung lượng pin", unit: "mAh" },
  os: { label: "Hệ điều hành" },
  weight: { label: "Trọng lượng", unit: "g" },
  color: { label: "Màu sắc" },
  camera: { label: "Camera" },
  gpu: { label: "Card đồ họa (GPU)" },
  screen_type: { label: "Công nghệ màn hình" },
  release_year: { label: "Năm ra mắt" },
};

export default function ProfilePage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [requests, setRequests] = useState<ProductDetailChangeRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter and search states
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRequest, setSelectedRequest] = useState<ProductDetailChangeRequestItem | null>(null);
  const [cancelingId, setCancelingId] = useState<string | null>(null);

  const handleCancelRequest = async (requestId: string) => {
    const confirmCancel = window.confirm("Bạn có chắc chắn muốn hủy yêu cầu chỉnh sửa này không?");
    if (!confirmCancel) return;

    setCancelingId(requestId);
    try {
      await api.products.cancelRequest(requestId);
      setRequests((prev) => prev.filter((r) => r.request_id !== requestId));
      setSelectedRequest(null);
    } catch (err) {
      console.error(err);
      alert("Lỗi khi hủy yêu cầu chỉnh sửa.");
    } finally {
      setCancelingId(null);
    }
  };

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login?next=/profile");
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    api.products
      .detailRequests()
      .then((items) => {
        if (active) setRequests(items);
      })
      .catch((err) => {
        console.error(err);
        if (active) setError("Không thể tải danh sách phiếu yêu cầu chỉnh sửa.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [isLoading, router, user]);

  const stats = useMemo(() => {
    const total = requests.length;
    const pending = requests.filter((r) => r.status === "pending").length;
    const processing = requests.filter((r) => r.status === "processing").length;
    const approved = requests.filter((r) => r.status === "approved").length;
    const rejected = requests.filter((r) => r.status === "rejected").length;

    return { total, pending, processing, approved, rejected };
  }, [requests]);

  const filteredRequests = useMemo(() => {
    return requests.filter((req) => {
      const matchStatus = statusFilter === "all" || req.status === statusFilter;
      const productName = (req.product_name || req.product_id).toLowerCase();
      const matchSearch = productName.includes(searchQuery.toLowerCase().trim());
      return matchStatus && matchSearch;
    });
  }, [requests, statusFilter, searchQuery]);

  const getRequestTitle = (req: ProductDetailChangeRequestItem) => {
    if (req.proposed_specs && Object.keys(req.proposed_specs).length > 0) {
      const keys = Object.keys(req.proposed_specs);
      const labels = keys.map((key) => {
        const specMeta = COMMON_SPEC_LABELS[key];
        return specMeta ? specMeta.label.toLowerCase() : key;
      });
      return `Cập nhật thông số (${labels.join(", ")})`;
    }
    if (req.proposed_description) return "Cập nhật mô tả sản phẩm";
    if (req.proposed_official_url) return "Cập nhật trang web chính thức";
    if (req.proposed_image_url) return "Cập nhật hình ảnh sản phẩm";
    return "Cập nhật thông tin sản phẩm";
  };

  const getRequestTypeIcon = (req: ProductDetailChangeRequestItem): "spec" | "activity" | "link" | "spark" => {
    if (req.proposed_specs && Object.keys(req.proposed_specs).length > 0) return "spec";
    if (req.proposed_description) return "activity";
    if (req.proposed_official_url) return "link";
    return "spark";
  };

  if (isLoading || loading) {
    return (
      <div className="grid min-h-[500px] place-items-center">
        <div className="flex flex-col items-center gap-3">
          <div className="spinner" />
          <p className="faint text-sm font-semibold">Đang tải dữ liệu tài khoản...</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <main className="mx-auto max-w-[1120px] px-6 py-10 pb-20">
      {/* Page header */}
      <div className="mb-8">
        <span className="chip brand mb-3">
          <Icon name="user" size={13} />
          Trang cá nhân
        </span>
        <h1 className="m-0 text-[30px] font-extrabold tracking-[-.02em]">Tài khoản của tôi</h1>
        <p className="muted mt-1.5 text-[15px]">Quản lý thông tin tài khoản và theo dõi trạng thái đề xuất đóng góp dữ liệu.</p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Column: User details & Stats */}
        <div className="lg:col-span-4 space-y-6">
          <Card className="overflow-hidden shadow-[var(--shadow-md)]">
            {/* Gradient Header banner */}
            <div className="h-24 bg-gradient-to-r from-violet-600 to-indigo-600" />

            <div className="relative px-6 pb-6 pt-0">
              {/* Avatar offset */}
              <div className="absolute -top-12 left-6 flex h-20 w-20 items-center justify-center rounded-2xl border-4 border-[var(--surface)] bg-gradient-to-br from-violet-400 to-fuchsia-500 text-[26px] font-black text-white shadow-md">
                {user.display_name.charAt(0).toUpperCase()}
              </div>

              <div className="pt-10">
                <h2 className="text-[20px] font-extrabold leading-tight">{user.display_name}</h2>
                <p className="muted text-sm mt-1">{user.email}</p>
              </div>

              <br />
              <hr className="divider my-5" />
              <br />

              {/* Stats details */}
              <div className="space-y-3.5">
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-[var(--text-3)]">Thống kê hoạt động</h3>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-[var(--surface-2)] p-3 text-center border border-[var(--border)]">
                    <div className="num text-xl font-extrabold text-[var(--text)]">{stats.total}</div>
                    <div className="faint text-[11px] font-semibold mt-0.5">Phiếu đã gửi</div>
                  </div>
                  <div className="rounded-xl bg-white dark:bg-amber-950/5 p-3 text-center border border-amber-100 dark:border-amber-900/30">
                    <div className="num text-xl font-extrabold text-amber-600 dark:text-amber-400">{stats.pending + stats.processing}</div>
                    <div className="faint text-[11px] font-semibold mt-0.5 text-amber-700/80 dark:text-amber-400/80">Đang xử lý</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-emerald-50 dark:bg-emerald-950/5 p-3 text-center border border-emerald-100 dark:border-emerald-900/30">
                    <div className="num text-xl font-extrabold text-emerald-600 dark:text-emerald-400">{stats.approved}</div>
                    <div className="faint text-[11px] font-semibold mt-0.5 text-emerald-700/80 dark:text-emerald-400/80">Đã duyệt</div>
                  </div>
                  <div className="rounded-xl bg-rose-50 dark:bg-rose-950/5 p-3 text-center border border-rose-100 dark:border-rose-900/30">
                    <div className="num text-xl font-extrabold text-rose-600 dark:text-rose-400">{stats.rejected}</div>
                    <div className="faint text-[11px] font-semibold mt-0.5 text-rose-700/80 dark:text-rose-400/80">Từ chối</div>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Right Column: History List */}
        <div className="lg:col-span-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-xl font-bold tracking-tight">Lịch sử phiếu đóng góp</h2>

            {/* Search inputs */}
            <div className="flex w-full items-center gap-3 sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-3)]">
                  <Icon name="search" size={15} />
                </span>
                <input
                  type="text"
                  placeholder="Tìm theo tên sản phẩm..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="focusable w-full rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] py-2 pl-9 pr-4 text-sm font-medium"
                />
              </div>
            </div>
          </div>

          {/* Status filters */}
          <div className="flex flex-wrap gap-2 border-b border-[var(--border)] pb-3">
            <button
              onClick={() => setStatusFilter("all")}
              className={`focusable rounded-full px-4 py-1.5 text-xs font-bold transition-all ${statusFilter === "all" ? "bg-violet-600 text-white shadow-sm" : "bg-[var(--surface-2)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
            >
              Tất cả ({stats.total})
            </button>
            <button
              onClick={() => setStatusFilter("pending")}
              className={`focusable rounded-full px-4 py-1.5 text-xs font-bold transition-all ${statusFilter === "pending" ? "bg-amber-500 text-white shadow-sm" : "bg-[var(--surface-2)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
            >
              Đang chờ ({stats.pending})
            </button>
            <button
              onClick={() => setStatusFilter("processing")}
              className={`focusable rounded-full px-4 py-1.5 text-xs font-bold transition-all ${statusFilter === "processing" ? "bg-blue-500 text-white shadow-sm" : "bg-[var(--surface-2)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
            >
              Đang xử lý ({stats.processing})
            </button>
            <button
              onClick={() => setStatusFilter("approved")}
              className={`focusable rounded-full px-4 py-1.5 text-xs font-bold transition-all ${statusFilter === "approved" ? "bg-emerald-600 text-white shadow-sm" : "bg-[var(--surface-2)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
            >
              Đã duyệt ({stats.approved})
            </button>
            <button
              onClick={() => setStatusFilter("rejected")}
              className={`focusable rounded-full px-4 py-1.5 text-xs font-bold transition-all ${statusFilter === "rejected" ? "bg-rose-500 text-white shadow-sm" : "bg-[var(--surface-2)] text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}
            >
              Từ chối ({stats.rejected})
            </button>
          </div>

          {/* History details */}
          {error ? (
            <Card className="border-[var(--neg)] p-5 text-sm text-[var(--neg)]">{error}</Card>
          ) : filteredRequests.length > 0 ? (
            <div className="space-y-3.5">
              {filteredRequests.map((req) => {
                const statusMeta = statusMapping[req.status];
                const typeIcon = getRequestTypeIcon(req);
                return (
                  <Card
                    key={req.request_id}
                    className="focusable transition-all hover:translate-x-0.5 hover:shadow-[var(--shadow-sm)] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div className="flex items-start gap-3.5">
                      <div className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[var(--primary-soft)] text-[var(--primary)]">
                        <Icon name={typeIcon} size={18} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-extrabold text-[15px] text-[var(--text)] tracking-tight">
                          {getRequestTitle(req)}
                        </h3>
                        <p className="faint mt-1 text-[13px] font-semibold truncate">
                          Sản phẩm: <span className="text-violet-600 dark:text-violet-400 font-bold">{req.product_name || req.product_id}</span>
                        </p>
                        <p className="faint text-[12px] mt-0.5 font-medium">
                          Mã phiếu: #{req.request_id.substring(0, 8)} • Ngày gửi: {formatDate(req.created_at)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0">
                      <Badge variant={statusMeta.variant} className="px-2.5 py-1 text-xs font-bold shrink-0">
                        {statusMeta.label}
                      </Badge>
                      {req.status === "pending" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCancelRequest(req.request_id);
                          }}
                          className="h-8 text-xs font-bold text-rose-600 hover:text-rose-700 hover:bg-rose-50 border-rose-200 hover:border-rose-300"
                          disabled={cancelingId === req.request_id}
                        >
                          Hủy
                        </Button>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedRequest(req)}
                        className="h-8 text-xs font-bold"
                      >
                        Chi tiết
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          ) : (
            <div className="card p-12 text-center">
              <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl bg-[var(--primary-soft)] text-[var(--primary)]">
                <Icon name="inbox" size={22} />
              </div>
              <h3 className="text-base font-bold">Không tìm thấy yêu cầu nào</h3>
              <p className="muted mx-auto mt-2 max-w-sm text-[13px]">
                {searchQuery || statusFilter !== "all"
                  ? "Hãy thử thay đổi từ khóa hoặc bộ lọc trạng thái."
                  : "Bạn chưa gửi yêu cầu chỉnh sửa thông số sản phẩm nào."}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Read-only details modal for the user */}
      <Modal
        open={!!selectedRequest}
        title={
          selectedRequest ? (
            <div>
              <h3 className="m-0 text-[18px] font-extrabold text-[var(--text)]">Chi tiết phiếu chỉnh sửa</h3>
              <div className="text-xs text-[var(--text-3)] font-medium mt-1">
                #{selectedRequest.request_id.substring(0, 8)} · Gửi ngày {formatDate(selectedRequest.created_at)}
              </div>
            </div>
          ) : ""
        }
        onClose={() => setSelectedRequest(null)}
      >
        {selectedRequest && (
          <div className="p-1 space-y-5">
            {/* Info Summary Panel */}
            <div className="rounded-[16px] bg-[var(--surface-2)] p-4 flex flex-col gap-3 shadow-sm border border-[var(--border)]">
              <div className="flex justify-between items-center text-sm">
                <span className="text-[var(--text-3)] font-semibold">Tên sản phẩm</span>
                <span className="font-extrabold text-violet-600 dark:text-violet-400">
                  {selectedRequest.product_name || selectedRequest.product_id}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm border-t border-[var(--border)] pt-2.5">
                <span className="text-[var(--text-3)] font-semibold">Loại đề xuất</span>
                <span className="font-bold text-[var(--text)]">
                  {selectedRequest.proposed_specs && Object.keys(selectedRequest.proposed_specs).length > 0
                    ? "Cập nhật thông số"
                    : selectedRequest.proposed_description
                      ? "Cập nhật mô tả"
                      : selectedRequest.proposed_official_url
                        ? "Cập nhật trang web"
                        : "Cập nhật hình ảnh"}
                </span>
              </div>
            </div>

            {/* Friendly content renderer */}
            <div>
              <div className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-2">Thông tin đề xuất thay đổi</div>

              <div className="rounded-2xl bg-[var(--primary-soft)]/40 dark:bg-[var(--primary-soft)]/10 p-4 border border-[var(--border)] space-y-4">
                {/* Proposed Specs */}
                {selectedRequest.proposed_specs && Object.keys(selectedRequest.proposed_specs).length > 0 && (
                  <div className="space-y-2 text-[13.5px]">
                    {Object.entries(selectedRequest.proposed_specs).map(([key, val]) => {
                      const specMeta = COMMON_SPEC_LABELS[key];
                      const label = specMeta ? specMeta.label : key;
                      const unit = specMeta && specMeta.unit ? ` (${specMeta.unit})` : "";
                      let displayValue = String(val);
                      if (val === true) displayValue = "Có";
                      else if (val === false) displayValue = "Không";

                      return (
                        <div key={key} className="flex justify-between border-b border-[var(--border)] py-2 last:border-0">
                          <span className="font-medium text-[var(--text-2)]">{label}{unit}:</span>
                          <span className="font-extrabold text-[var(--text)]">{displayValue}</span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Proposed Description */}
                {selectedRequest.proposed_description && (
                  <div className="text-[13.5px] leading-relaxed">
                    <span className="block text-[11px] font-bold text-violet-700 dark:text-violet-400 uppercase tracking-wider mb-1">Mô tả sản phẩm</span>
                    <p className="m-0 font-bold text-violet-950 dark:text-violet-200">{selectedRequest.proposed_description}</p>
                  </div>
                )}

                {/* Proposed Official URL */}
                {selectedRequest.proposed_official_url && (
                  <div className="text-[13.5px]">
                    <span className="block text-[11px] font-bold text-violet-700 dark:text-violet-400 uppercase tracking-wider mb-1">Trang web chính thức</span>
                    <a
                      href={selectedRequest.proposed_official_url}
                      target="_blank"
                      rel="noreferrer"
                      className="underline font-bold text-violet-900 hover:text-violet-700 dark:text-violet-300 dark:hover:text-violet-200 break-all"
                    >
                      {selectedRequest.proposed_official_url}
                    </a>
                  </div>
                )}

                {/* Proposed Image URL */}
                {selectedRequest.proposed_image_url && (
                  <div className="text-[13.5px] space-y-2">
                    <span className="block text-[11px] font-bold text-violet-700 dark:text-violet-400 uppercase tracking-wider">Ảnh đề xuất</span>
                    <a
                      href={selectedRequest.proposed_image_url}
                      target="_blank"
                      rel="noreferrer"
                      className="underline font-bold text-violet-900 hover:text-violet-700 dark:text-violet-300 dark:hover:text-violet-200 break-all block"
                    >
                      {selectedRequest.proposed_image_url}
                    </a>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={selectedRequest.proposed_image_url}
                      alt="Đề xuất"
                      className="max-h-32 rounded-xl object-contain border border-violet-200/50 dark:border-violet-900/30 mt-2"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Status & Handler details */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-1.5 block">Trạng thái phiếu</label>
                <div className="flex">
                  <Badge variant={statusMapping[selectedRequest.status].variant} className="h-10 flex items-center px-4 rounded-xl font-bold text-[13px] justify-center">
                    {statusMapping[selectedRequest.status].label}
                  </Badge>
                </div>
              </div>
              <div>
                <label className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider mb-1.5 block">Người xử lý</label>
                <div className="h-10 flex items-center px-3 rounded-xl border border-[var(--border)] bg-[var(--surface-3)] font-medium text-[13px] text-[var(--text-3)] truncate">
                  {selectedRequest.reviewed_by || "Chưa phân công"}
                </div>
              </div>
            </div>

            {/* Review Notes from admin */}
            {(selectedRequest.status === "approved" || selectedRequest.status === "rejected") && (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-2)] p-4 space-y-1.5">
                <label className="text-[11px] font-bold text-[var(--text-3)] uppercase tracking-wider block">Ghi chú từ quản trị viên</label>
                <p className="text-sm font-semibold text-[var(--text)] m-0 leading-relaxed">
                  {selectedRequest.review_note || "Không có ghi chú cụ thể."}
                </p>
                {selectedRequest.reviewed_at && (
                  <span className="block text-[11px] faint mt-1 font-medium">
                    Thời gian xử lý: {formatDate(selectedRequest.reviewed_at)}
                  </span>
                )}
              </div>
            )}

            {/* Close / Action buttons */}
            <div className="flex justify-end gap-3 pt-2">
              {selectedRequest.status === "pending" && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => handleCancelRequest(selectedRequest.request_id)}
                  className="w-full sm:w-32 font-bold text-rose-600 hover:text-rose-750 hover:bg-rose-50/50 border-rose-200"
                  disabled={cancelingId === selectedRequest.request_id}
                >
                  Hủy yêu cầu
                </Button>
              )}
              <Button type="button" onClick={() => setSelectedRequest(null)} className="w-full sm:w-28 font-bold">
                Đóng
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </main>
  );
}
