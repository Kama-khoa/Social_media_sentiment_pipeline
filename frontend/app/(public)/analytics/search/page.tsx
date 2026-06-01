"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { SearchResultItem } from "@/lib/types";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { ControversyBadgeDark } from "@/components/public/ControversyBadgeDark";

const CATEGORIES = [
  { value: "", label: "Tất cả danh mục" },
  { value: "Điện thoại", label: "Điện thoại" },
  { value: "Laptop", label: "Laptop" },
  { value: "Tai nghe", label: "Tai nghe" },
  { value: "Smarthome", label: "Smarthome" },
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() && !category) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.search(query, category);
      setResults(data.results);
      setSearched(true);
    } catch {
      setError("Không thể thực hiện tìm kiếm. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-100">Tìm kiếm sản phẩm</h1>
        <p className="text-slate-400 text-sm mt-1">Tra cứu phân tích sentiment cho bất kỳ sản phẩm công nghệ nào</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3 mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Nhập tên sản phẩm hoặc thương hiệu…"
          className="flex-1 bg-slate-800 border border-slate-600 text-slate-200 placeholder-slate-500 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="bg-slate-800 border border-slate-600 text-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-cyan-500"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={loading}
          className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? "Đang tìm…" : "Tìm kiếm"}
        </button>
      </form>

      {error && (
        <div className="text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg p-4 text-sm mb-4">
          {error}
        </div>
      )}

      {searched && results.length === 0 && !loading && (
        <div className="text-center py-16 text-slate-500">
          <div className="text-4xl mb-3">🔍</div>
          <div className="text-lg font-medium text-slate-400 mb-1">Không tìm thấy kết quả</div>
          <div className="text-sm">Thử từ khóa khác hoặc bỏ bộ lọc danh mục</div>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs text-slate-500 mb-2">{results.length} kết quả</div>
          {results.map((item) => (
            <div
              key={item.product_id}
              className="bg-slate-800/60 border border-slate-700/50 hover:border-cyan-500/40 rounded-xl p-4 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/analytics/products/${item.product_id}`}
                    className="text-slate-100 font-semibold hover:text-cyan-400 transition-colors"
                  >
                    {item.product_name}
                  </Link>
                  <div className="text-xs text-slate-500 mt-0.5">{item.brand} · {item.category}</div>
                  <div className="mt-2 flex items-center gap-3">
                    <ControversyBadgeDark label={item.controversy_label} />
                    <span className="text-xs text-slate-500">{item.total_mentions.toLocaleString()} lượt đề cập</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-cyan-400 font-bold text-lg">{(item.bayesian_score * 100).toFixed(1)}</div>
                  <div className="text-xs text-slate-500">điểm Bayesian</div>
                  <div className="mt-2 w-32">
                    <SentimentBar
                      positivePct={item.total_mentions > 0 ? 50 : 0}
                      negativePct={item.total_mentions > 0 ? 25 : 0}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!searched && !loading && (
        <div className="text-center py-20 text-slate-600">
          <div className="text-5xl mb-4">📊</div>
          <div className="text-slate-500">Nhập tên sản phẩm để xem phân tích sentiment</div>
        </div>
      )}
    </div>
  );
}
