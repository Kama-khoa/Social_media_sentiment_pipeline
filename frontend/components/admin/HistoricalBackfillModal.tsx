import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Modal } from "./Modal";
import { Button } from "../ui/button";
import { Icon } from "../shared/Icon";
import { Select } from "../ui/select";

interface HistoricalBackfillModalProps {
  open: boolean;
  onClose: () => void;
}

export function HistoricalBackfillModal({ open, onClose }: HistoricalBackfillModalProps) {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [limit, setLimit] = useState("5");

  useEffect(() => {
    if (open) {
      loadStatus();
    }
  }, [open]);

  async function loadStatus() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.admin.backfill.status();
      setStatus(data);
    } catch (err: any) {
      setError(err?.detail || "Lỗi khi tải trạng thái backfill");
    } finally {
      setLoading(false);
    }
  }

  async function handleTrigger() {
    setTriggering(true);
    setError(null);
    try {
      await api.admin.backfill.triggerHistorical(parseInt(limit, 10));
      await loadStatus();
    } catch (err: any) {
      setError(err?.detail || "Lỗi khi trigger backfill");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <Modal open={open} title="Quét kênh cũ (Historical Backfill)" onClose={onClose}>
      <div className="space-y-5">
        <p className="text-sm text-slate-600">
          Historical Backfill sẽ gọi Airflow để quét các kênh chưa từng được quét lịch sử (historical_scan = false).
          Quá trình này sử dụng yt-dlp để lấy toàn bộ video cũ (không tốn API quota) và xếp hàng vào DB.
        </p>

        {error && <div className="bg-rose-50 text-rose-700 text-xs p-3 rounded-md">{error}</div>}

        {loading ? (
          <div className="flex justify-center p-6"><div className="spinner" /></div>
        ) : status ? (
          <div className="bg-slate-50 border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium">Trạng thái:</span>
              {status.is_running ? (
                <span className="text-xs bg-amber-100 text-amber-700 font-bold px-2 py-1 rounded">Đang chạy</span>
              ) : (
                <span className="text-xs bg-slate-200 text-slate-600 font-bold px-2 py-1 rounded">Sẵn sàng</span>
              )}
            </div>
            
            <div className="flex justify-between text-sm mb-1">
              <span className="text-slate-500">Kênh chờ quét:</span>
              <span className="font-mono font-bold">{status.channels_remaining} / {status.total_channels}</span>
            </div>
            
            <div className="w-full bg-slate-200 rounded-full h-2 mb-4">
              <div 
                className="bg-indigo-500 h-2 rounded-full transition-all" 
                style={{ width: `${Math.max(0, Math.min(100, ((status.total_channels - status.channels_remaining) / (status.total_channels || 1)) * 100))}%` }}
              />
            </div>
            
            {status.current_dag_run_id && (
              <div className="text-xs text-slate-400 font-mono break-all">
                Run ID: {status.current_dag_run_id}
              </div>
            )}
          </div>
        ) : null}

        <div className="flex items-end gap-3 pt-2">
          <div className="flex-1">
            <label className="block text-xs font-medium text-slate-700 mb-1">Số kênh quét mỗi đợt</label>
            <Select value={limit} onChange={(e) => setLimit(e.target.value)} disabled={triggering || status?.is_running}>
              <option value="1">1 kênh (Test)</option>
              <option value="5">5 kênh</option>
              <option value="10">10 kênh</option>
              <option value="20">20 kênh</option>
              <option value="50">50 kênh</option>
            </Select>
          </div>
          <Button 
            onClick={handleTrigger} 
            disabled={triggering || status?.is_running || status?.channels_remaining === 0}
            className="mb-[1px]"
          >
            <Icon name="play" size={14} className="mr-1.5" />
            {triggering ? "Đang gửi yêu cầu..." : "Bắt đầu quét"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
