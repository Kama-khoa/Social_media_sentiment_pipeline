import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Modal } from "./Modal";
import { Button } from "../ui/button";
import { Icon } from "../shared/Icon";

interface ChannelSuggestionModalProps {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
}

export function ChannelSuggestionModal({ open, onClose, onAdded }: ChannelSuggestionModalProps) {
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      loadSuggestions();
    }
  }, [open]);

  async function loadSuggestions() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.admin.channels.suggestions.list();
      setSuggestions(data);
    } catch (err: any) {
      setError(err?.detail || "Lỗi khi tải gợi ý kênh");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(channel: any) {
    setProcessingId(channel.channel_id);
    setError(null);
    try {
      await api.admin.channels.suggestions.approve({
        channel_id: channel.channel_id,
        channel_name: `Kênh ${channel.channel_id}`,
        channel_url: `https://www.youtube.com/channel/${channel.channel_id}`,
      });
      setSuggestions((prev) => prev.filter((c) => c.channel_id !== channel.channel_id));
      onAdded();
    } catch (err: any) {
      setError(err?.detail || "Lỗi khi thêm kênh");
    } finally {
      setProcessingId(null);
    }
  }

  return (
    <Modal open={open} title="Gợi ý kênh tiềm năng" onClose={onClose}>
      <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
        <p className="text-sm text-slate-500">
          Các kênh YouTube có chứa video liên quan nhưng chưa có trong hệ thống (tự động phân tích từ kết quả tìm kiếm).
        </p>
        
        {error && <div className="bg-rose-50 text-rose-700 text-xs p-3 rounded-md">{error}</div>}
        
        {loading ? (
          <div className="flex justify-center p-8"><div className="spinner" /></div>
        ) : suggestions.length === 0 ? (
          <div className="text-center p-8 text-sm text-slate-500">
            Không có gợi ý kênh nào mới.
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {suggestions.map((ch) => (
              <div key={ch.channel_id} className="border border-slate-200 rounded-lg p-3 bg-slate-50 flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-sm text-slate-800">{ch.channel_id}</span>
                    <span className="text-xs text-slate-500 bg-white border px-1.5 py-0.5 rounded-md">
                      {ch.video_count} video liên quan
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Video mới nhất: {new Date(ch.earliest_video_at).toLocaleDateString('vi-VN')}
                  </div>
                  <div className="mt-2 space-y-1">
                    {ch.sample_titles.slice(0, 2).map((title: string, idx: number) => (
                      <div key={idx} className="text-xs truncate text-slate-600 bg-white border border-slate-100 px-2 py-1 rounded">
                        {title}
                      </div>
                    ))}
                  </div>
                </div>
                <Button 
                  size="sm" 
                  disabled={processingId === ch.channel_id}
                  onClick={() => handleApprove(ch)}
                  className="shrink-0"
                >
                  <Icon name="plus" size={14} className="mr-1.5" />
                  Thêm kênh
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
