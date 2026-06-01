"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";
import type { TopProduct } from "@/lib/types";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { ControversyBadgeDark } from "@/components/public/ControversyBadgeDark";

const CATEGORIES = [
  { slug: "all", label: "Tất cả" },
  { slug: "dien_thoai", label: "Điện thoại" },
  { slug: "laptop", label: "Laptop" },
  { slug: "tai_nghe", label: "Tai nghe" },
  { slug: "smarthome", label: "Smarthome" },
];

function LoadingRow() {
  return (
    <tr className="border-b border-slate-700/50">
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i} className="px-4 py-4">
          <div className="h-4 bg-slate-700 rounded animate-pulse" />
        </td>
      ))}
    </tr>
  );
}

export default function TopProductsPage() {
  const [category, setCategory] = useState("all");
  const [products, setProducts] = useState<TopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.products
      .top(category)
      .then(setProducts)
      .catch(() => setError("Không thể tải dữ liệu. Vui lòng thử lại."))
      .finally(() => setLoading(false));
  }, [category]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Bảng xếp hạng sản phẩm công nghệ</h1>
        <p className="text-slate-400 text-sm mt-1">
          Xếp hạng dựa trên điểm Bayesian từ phân tích bình luận YouTube · Cập nhật hằng ngày
        </p>
      </div>

      {/* Category tabs */}
      <div className="flex gap-1 mb-6 bg-slate-800/50 p-1 rounded-lg w-fit">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.slug}
            onClick={() => setCategory(cat.slug)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              category === cat.slug
                ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-700/50"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg p-4 text-sm mb-4">
          {error}
        </div>
      )}

      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-xs uppercase tracking-wider">
              <th className="px-4 py-3 text-left w-12">Hạng</th>
              <th className="px-4 py-3 text-left">Sản phẩm</th>
              <th className="px-4 py-3 text-right w-24">Điểm</th>
              <th className="px-4 py-3 text-left w-40">Sentiment</th>
              <th className="px-4 py-3 text-left w-32">Đánh giá</th>
              <th className="px-4 py-3 text-left w-28">Nổi bật</th>
              <th className="px-4 py-3 text-center w-20">Chi tiết</th>
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 8 }).map((_, i) => <LoadingRow key={i} />)
              : products.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-16 text-center text-slate-500">
                      Đang cập nhật dữ liệu phân tích…
                    </td>
                  </tr>
                )
              : products.map((p) => (
                  <tr
                    key={p.product_id}
                    className="border-b border-slate-700/40 hover:bg-slate-700/30 transition-colors"
                  >
                    <td className="px-4 py-3.5">
                      <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                        p.rank === 1 ? "bg-amber-500/20 text-amber-400" :
                        p.rank === 2 ? "bg-slate-500/20 text-slate-300" :
                        p.rank === 3 ? "bg-orange-800/20 text-orange-400" :
                        "text-slate-500"
                      }`}>
                        {p.rank}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-medium text-slate-100">{p.product_name}</div>
                      <div className="text-xs text-slate-500">{p.brand} · {p.category}</div>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <span className="text-cyan-400 font-semibold">
                        {(p.bayesian_score * 100).toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="space-y-1">
                        <SentimentBar positivePct={p.positive_pct} negativePct={p.negative_pct} />
                        <div className="flex justify-between text-xs text-slate-500">
                          <span className="text-emerald-500">{p.positive_pct.toFixed(0)}%+</span>
                          <span className="text-rose-500">{p.negative_pct.toFixed(0)}%-</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <ControversyBadgeDark label={p.controversy_label} />
                    </td>
                    <td className="px-4 py-3.5 text-slate-400 text-xs">{p.top_aspect ?? "—"}</td>
                    <td className="px-4 py-3.5 text-center">
                      <Link
                        href={`/analytics/products/${p.product_id}`}
                        className="text-xs text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
                      >
                        Xem →
                      </Link>
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>

        {!loading && products.length > 0 && (
          <div className="px-4 py-3 border-t border-slate-700/40 text-xs text-slate-500">
            {products.length} sản phẩm · {products.reduce((s, p) => s + p.total_mentions, 0).toLocaleString()} lượt đề cập
          </div>
        )}
      </div>
    </div>
  );
}
