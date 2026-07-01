"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Modal } from "./Modal";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/shared/Icon";

interface CrawlProgressProps {
  open: boolean;
  taskId: string | null;
  onClose: () => void;
  onComplete?: () => void;
  productName?: string;
}

export function CrawlProgress({ open, taskId, onClose, onComplete, productName }: CrawlProgressProps) {
  const [status, setStatus] = useState<"pending" | "running" | "success" | "failed">("pending");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("Đang khởi tạo tiến trình...");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !taskId) return;

    setStatus("pending");
    setProgress(0);
    setMessage("Đang xếp hàng tiến trình...");
    setError(null);

    let intervalId: NodeJS.Timeout;

    const checkStatus = async () => {
      try {
        const res = await api.admin.products.crawlTaskStatus(taskId);
        setStatus(res.status as any);
        setProgress(res.progress);
        setMessage(res.message);

        if (res.status === "success") {
          clearInterval(intervalId);
          if (onComplete) {
            onComplete();
          }
        } else if (res.status === "failed") {
          clearInterval(intervalId);
          setError(res.error || "Có lỗi bất ngờ xảy ra trong quá trình thu thập.");
        }
      } catch (err) {
        console.error("Lỗi khi kiểm tra trạng thái task:", err);
      }
    };

    // Chạy lần đầu ngay lập tức
    void checkStatus();

    // Thiết lập polling mỗi 3 giây
    intervalId = setInterval(checkStatus, 3000);

    return () => {
      clearInterval(intervalId);
    };
  }, [open, taskId, onComplete]);

  if (!open || !taskId) return null;

  const getStatusColor = () => {
    switch (status) {
      case "success": return "text-emerald-500 bg-emerald-50 border-emerald-200";
      case "failed": return "text-rose-500 bg-rose-50 border-rose-200";
      default: return "text-blue-500 bg-blue-50 border-blue-200";
    }
  };

  const isFinished = status === "success" || status === "failed";

  return (
    <Modal open={open} title="Tiến trình thu thập dữ liệu" onClose={onClose} size="lg">
      <div className="space-y-6">
        <div>
          <div className="text-[13.5px] font-semibold text-[var(--text-3)]">Sản phẩm thu thập</div>
          <div className="text-[16px] font-bold text-[var(--text)] mt-0.5">{productName || "Sản phẩm"}</div>
        </div>

        {/* Trạng thái chính */}
        <div className={`rounded-xl border p-4 flex items-start gap-3 ${getStatusColor()}`}>
          <div className="mt-0.5">
            {status === "success" && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white text-xs">✓</span>
            )}
            {status === "failed" && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rose-500 text-white text-xs font-bold">!</span>
            )}
            {status !== "success" && status !== "failed" && (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" />
            )}
          </div>
          <div className="flex-1">
            <div className="text-sm font-bold text-[var(--text)] capitalize">
              {status === "pending" && "Đang chuẩn bị"}
              {status === "running" && "Đang xử lý"}
              {status === "success" && "Thành công"}
              {status === "failed" && "Thất bại"}
            </div>
            <div className="text-[13px] font-medium text-[var(--text-2)] mt-1">{message}</div>
          </div>
        </div>

        {/* Thanh tiến trình */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs font-bold text-[var(--text-2)]">
            <span>Tiến độ hoàn thành</span>
            <span className="num font-semibold">{progress}%</span>
          </div>
          <div className="w-full bg-[var(--surface-3)] h-3 rounded-full overflow-hidden p-0.5 border border-[var(--border)]">
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out ${
                status === "success"
                  ? "bg-emerald-500"
                  : status === "failed"
                  ? "bg-rose-500"
                  : "bg-[var(--primary)]"
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Chi tiết lỗi nếu có */}
        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
            <div className="text-xs font-bold text-rose-700 uppercase tracking-wider mb-2">Chi tiết lỗi từ hệ thống:</div>
            <pre className="max-h-[150px] overflow-y-auto font-mono text-[11.5px] text-rose-600 bg-rose-100/50 p-3 rounded-lg whitespace-pre-wrap break-all leading-normal">
              {error}
            </pre>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-3 pt-2">
          {!isFinished && (
            <Button variant="outline" onClick={onClose}>
              Thu nhỏ
            </Button>
          )}
          {isFinished && (
            <Button
              onClick={onClose}
              className="min-w-[100px]"
            >
              Đóng
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
