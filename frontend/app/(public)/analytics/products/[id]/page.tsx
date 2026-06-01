"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";
import type { ProductDetail } from "@/lib/types";
import { AspectRadarChart } from "@/components/charts/AspectRadarChart";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { ControversyBadgeDark } from "@/components/public/ControversyBadgeDark";

function Skeleton({ className }: { className?: string }) {
  return <div className={`bg-slate-700 rounded animate-pulse ${className ?? ""}`} />;
}

function ProductDetailSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <Skeleton className="h-5 w-32" />
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6 space-y-3">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-40" />
        <div className="flex gap-2 mt-2">
          <Skeleton className="h-6 w-20 rounded-full" />
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
      </div>
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<ProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.products
      .aspects(id)
      .then(setData)
      .catch(() => setError("Không thể tải dữ liệu sản phẩm."))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <ProductDetailSkeleton />;

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Link href="/analytics/top-products" className="text-slate-400 hover:text-cyan-400 text-sm transition-colors">
          ← Bảng xếp hạng
        </Link>
        <div className="mt-8 text-center py-16 text-slate-500">
          <div className="text-4xl mb-3">⚠</div>
          <div className="text-slate-400">{error ?? "Không tìm thấy sản phẩm."}</div>
        </div>
      </div>
    );
  }

  const totalMentions = data.total_mentions;
  const overallPositivePct =
    data.aspects.length > 0
      ? data.aspects.reduce((s, a) => s + a.positive_pct, 0) / data.aspects.length
      : 0;
  const overallNegativePct =
    data.aspects.length > 0
      ? data.aspects.reduce((s, a) => s + a.negative_pct, 0) / data.aspects.length
      : 0;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <Link href="/analytics/top-products" className="inline-flex items-center gap-1.5 text-slate-400 hover:text-cyan-400 text-sm transition-colors">
        ← Bảng xếp hạng
      </Link>

      {/* Product header */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">{data.product_name}</h1>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-300 border border-slate-600">
                {data.brand}
              </span>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                {data.category}
              </span>
              <ControversyBadgeDark label={data.controversy_label} />
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-3xl font-bold text-cyan-400">
              {(data.bayesian_score * 100).toFixed(1)}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">điểm Bayesian</div>
            <div className="text-xs text-slate-500 mt-1">
              {totalMentions.toLocaleString()} lượt đề cập
            </div>
          </div>
        </div>

        <div className="mt-4 space-y-1">
          <SentimentBar positivePct={overallPositivePct} negativePct={overallNegativePct} />
          <div className="flex justify-between text-xs text-slate-500">
            <span className="text-emerald-400">{overallPositivePct.toFixed(0)}% tích cực</span>
            <span className="text-rose-400">{overallNegativePct.toFixed(0)}% tiêu cực</span>
          </div>
        </div>
      </div>

      {/* Aspect radar chart */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
          Phân tích theo khía cạnh
        </h2>
        <AspectRadarChart aspects={data.aspects} />
      </div>

      {/* Aspect breakdown table */}
      {data.aspects.length > 0 && (
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400 text-xs uppercase tracking-wider">
                <th className="px-4 py-3 text-left">Khía cạnh</th>
                <th className="px-4 py-3 text-right w-24">Đề cập</th>
                <th className="px-4 py-3 text-right w-24">Tích cực</th>
                <th className="px-4 py-3 text-right w-24">Tiêu cực</th>
                <th className="px-4 py-3 text-right w-24">Trung lập</th>
              </tr>
            </thead>
            <tbody>
              {data.aspects.map((a) => (
                <tr key={a.aspect_label} className="border-b border-slate-700/40 hover:bg-slate-700/20 transition-colors">
                  <td className="px-4 py-3 font-medium text-slate-200">{a.aspect_label}</td>
                  <td className="px-4 py-3 text-right text-slate-400">{a.total_mentions.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-emerald-400">
                    {a.positive_count.toLocaleString()}
                    <span className="text-slate-500 text-xs ml-1">({a.positive_pct.toFixed(0)}%)</span>
                  </td>
                  <td className="px-4 py-3 text-right text-rose-400">
                    {a.negative_count.toLocaleString()}
                    <span className="text-slate-500 text-xs ml-1">({a.negative_pct.toFixed(0)}%)</span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-400">
                    {a.neutral_count.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Link to attribution */}
      <div className="flex justify-end">
        <Link
          href={`/analytics/products/${id}/attribution`}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 hover:text-cyan-400 text-sm font-medium rounded-lg border border-slate-600 transition-colors"
        >
          Xem phân tích biến động →
        </Link>
      </div>
    </div>
  );
}
