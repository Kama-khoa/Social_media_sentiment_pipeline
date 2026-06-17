"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { Modal } from "@/components/admin/Modal";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Icon } from "@/components/shared/Icon";

type SuggestionItem = {
  keyword_id: string;
  keyword_text: string;
  search_cluster: string | null;
  match_reason: string | null;
  similarity_score: number | null;
};

export function KeywordSuggestionModal({ open, productId, onClose }: { open: boolean, productId: string | null, onClose: () => void }) {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [linking, setLinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newKeyword, setNewKeyword] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (open && productId) {
      loadSuggestions();
    } else {
      setSuggestions([]);
      setSelectedIds(new Set());
      setError(null);
      setNewKeyword("");
    }
  }, [open, productId]);

  async function loadSuggestions() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.admin.keywords.suggest(productId!);
      setSuggestions(data);
      setSelectedIds(new Set(data.map((item) => item.keyword_id)));
    } catch (err: any) {
      setError(err?.detail ?? "Không thể tải danh sách gợi ý.");
    } finally {
      setLoading(false);
    }
  }

  function toggle(id: string) {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  }

  async function handleLink() {
    if (!productId || selectedIds.size === 0) return;
    setLinking(true);
    setError(null);
    try {
      await api.admin.keywords.bulkLink({
        keyword_ids: Array.from(selectedIds),
        product_id: productId,
      });
      onClose();
    } catch (err: any) {
      setError(err?.detail ?? "Không thể liên kết từ khóa.");
    } finally {
      setLinking(false);
    }
  }

  async function handleCreateNew() {
    if (!newKeyword.trim() || !productId) return;
    setCreating(true);
    setError(null);
    try {
      await api.admin.keywords.create({
        keyword_text: newKeyword.trim(),
        search_cluster: productId,
      });
      onClose();
    } catch (err: any) {
      setError(err?.detail ?? "Không thể tạo từ khóa.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <Modal open={open} title="Gợi ý từ khóa liên kết" onClose={onClose}>
      <div className="space-y-4">
        <div>
          <span className="text-sm text-slate-500">Sản phẩm mục tiêu:</span>
          <span className="ml-2 font-bold text-slate-800">{productId}</span>
        </div>

        {error && <div className="text-sm text-rose-600 bg-rose-50 p-3 rounded border border-rose-200">{error}</div>}

        {loading ? (
          <div className="py-8 flex justify-center text-slate-400">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-current border-t-transparent" />
          </div>
        ) : suggestions.length === 0 ? (
          <div className="py-8 text-center text-sm text-slate-500 space-y-4">
            <p>Hiện tại chưa có từ khóa tự do nào phù hợp để liên kết với sản phẩm này.</p>
            <div className="flex flex-col items-center gap-2 pt-4 max-w-xs mx-auto">
              <Input 
                placeholder="Nhập từ khóa mới..." 
                value={newKeyword} 
                onChange={(e) => setNewKeyword(e.target.value)} 
                disabled={creating}
              />
              <Button 
                className="w-full" 
                onClick={handleCreateNew} 
                disabled={!newKeyword.trim() || creating}
              >
                <Icon name="plus" size={16} className="mr-1.5" />
                {creating ? "Đang tạo..." : "Tạo & Liên kết ngay"}
              </Button>
            </div>
          </div>
        ) : (
          <div>
            <div className="mb-2 text-sm font-medium text-slate-700 flex justify-between items-center">
              <span>Đã chọn {selectedIds.size}/{suggestions.length} từ khóa</span>
              <div className="space-x-2">
                <button type="button" onClick={() => setSelectedIds(new Set(suggestions.map((s) => s.keyword_id)))} className="text-indigo-600 hover:text-indigo-800 text-xs font-semibold">Chọn tất cả</button>
                <button type="button" onClick={() => setSelectedIds(new Set())} className="text-slate-500 hover:text-slate-700 text-xs font-semibold">Bỏ chọn</button>
              </div>
            </div>
            <div className="max-h-60 overflow-y-auto space-y-2 border border-slate-200 rounded-lg p-2 bg-slate-50">
              {suggestions.map((item) => (
                <label key={item.keyword_id} className="flex items-center gap-3 p-2 rounded hover:bg-white border border-transparent hover:border-slate-200 cursor-pointer transition-colors">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.keyword_id)}
                    onChange={() => toggle(item.keyword_id)}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-slate-800 text-sm">{item.keyword_text}</div>
                    <div className="text-xs text-slate-400">
                      ID: {item.keyword_id} {item.search_cluster && `• Nhóm: ${item.search_cluster}`}
                    </div>
                  </div>
                  {item.similarity_score !== null && (
                    <Badge variant={item.similarity_score > 80 ? "brand" : "outline"} className="text-[10px]">
                      {item.similarity_score}% khớp
                    </Badge>
                  )}
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Button variant="outline" onClick={onClose} disabled={linking}>Hủy</Button>
          <Button onClick={handleLink} disabled={loading || linking || selectedIds.size === 0}>
            {linking ? "Đang liên kết..." : "Liên kết từ khóa"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
