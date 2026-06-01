"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { UserDashboardData } from "@/lib/types";
import { ControversyBadge } from "@/components/shared/ControversyBadge";

function CategoryCard({ label, mention_count, week_change_pct }: { label: string; mention_count: number; week_change_pct: number }) {
  const isPositive = week_change_pct >= 0;
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-sm transition-shadow">
      <p className="text-xs text-slate-500 font-medium mb-1">{label}</p>
      <p className="text-2xl font-semibold text-slate-800">{mention_count.toLocaleString("vi-VN")}</p>
      <p className="text-xs mt-1">
        <span className={`font-medium ${isPositive ? "text-emerald-600" : "text-rose-600"}`}>
          {isPositive ? "+" : ""}{week_change_pct.toFixed(1)}%
        </span>
        <span className="text-slate-400 ml-1">so với tuần trước</span>
      </p>
    </div>
  );
}

function SentimentBar({ positive_pct, negative_pct }: { positive_pct: number; negative_pct: number }) {
  const neutral_pct = 100 - positive_pct - negative_pct;
  return (
    <div className="flex items-center gap-1 w-32">
      <div
        className="h-1.5 rounded-l-full bg-emerald-400"
        style={{ width: `${positive_pct}%` }}
        title={`Tích cực ${positive_pct.toFixed(0)}%`}
      />
      <div
        className="h-1.5 bg-slate-300"
        style={{ width: `${neutral_pct}%` }}
        title={`Trung lập ${neutral_pct.toFixed(0)}%`}
      />
      <div
        className="h-1.5 rounded-r-full bg-rose-400"
        style={{ width: `${negative_pct}%` }}
        title={`Tiêu cực ${negative_pct.toFixed(0)}%`}
      />
    </div>
  );
}

export function UserDashboard() {
  const [data, setData] = useState<UserDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.dashboard
      .user()
      .then(setData)
      .catch(() => setError("Không thể tải dữ liệu"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 h-24 animate-pulse">
              <div className="h-3 bg-slate-100 rounded w-1/2 mb-2" />
              <div className="h-7 bg-slate-100 rounded w-2/3 mb-2" />
              <div className="h-3 bg-slate-100 rounded w-1/3" />
            </div>
          ))}
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4 h-64 animate-pulse" />
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 h-40 animate-pulse" />
          <div className="bg-white rounded-xl border border-slate-200 p-4 h-40 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-rose-700 text-sm">{error || "Lỗi không xác định"}</div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Tổng quan</h2>
          <p className="text-sm text-slate-500 mt-0.5">Dữ liệu tính đến {new Date(data.as_of_date).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })}</p>
        </div>
      </div>

      {/* Category stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {data.category_stats.map((s) => (
          <CategoryCard key={s.category} {...s} />
        ))}
      </div>

      {/* Top products */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Top sản phẩm nổi bật</h3>
          <span className="text-xs text-slate-400">Cập nhật hôm nay</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400 w-10">#</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Sản phẩm</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Điểm</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Tranh cãi</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Đề cập</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Cảm xúc</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Khía cạnh nổi bật</th>
              </tr>
            </thead>
            <tbody>
              {data.top_products.map((p) => (
                <tr key={p.product_id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors cursor-pointer">
                  <td className="px-5 py-3.5 text-slate-400 font-medium text-xs">{p.rank}</td>
                  <td className="px-5 py-3.5">
                    <div>
                      <p className="font-medium text-slate-800">{p.product_name}</p>
                      <p className="text-xs text-slate-400">{p.brand} · {p.category}</p>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="font-semibold text-indigo-700">{p.bayesian_score.toFixed(2)}</span>
                  </td>
                  <td className="px-5 py-3.5">
                    <ControversyBadge label={p.controversy_label} />
                  </td>
                  <td className="px-5 py-3.5 text-slate-600 text-xs">{p.total_mentions.toLocaleString("vi-VN")}</td>
                  <td className="px-5 py-3.5">
                    <SentimentBar positive_pct={p.positive_pct} negative_pct={p.negative_pct} />
                    <p className="text-xs text-slate-400 mt-0.5">{p.positive_pct.toFixed(0)}% tích cực</p>
                  </td>
                  <td className="px-5 py-3.5">
                    {p.top_aspect && (
                      <span className="inline-flex px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md text-xs">{p.top_aspect}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Causal events */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Sự kiện tương quan gần nhất</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {data.latest_causal_events.map((ev, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-sm transition-shadow">
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                  ev.sentiment_direction === "POSITIVE" ? "bg-emerald-100" : "bg-rose-100"
                }`}>
                  <svg className={`w-4 h-4 ${ev.sentiment_direction === "POSITIVE" ? "text-emerald-600" : "text-rose-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ev.sentiment_direction === "POSITIVE" ? "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" : "M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"} />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-slate-800">{ev.product_name}</span>
                    <span className="text-xs text-slate-400">
                      {new Date(ev.change_point_date).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" })}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 line-clamp-2 mb-2">{ev.explanation_text}</p>
                  <div className="flex items-center gap-1.5">
                    <svg className="w-3 h-3 text-slate-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
                    </svg>
                    <span className="text-xs text-slate-500 truncate">{ev.event_video_title}</span>
                    <span className="text-xs text-slate-400 shrink-0">· {(ev.event_view_count / 1_000_000).toFixed(1)}M lượt xem</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
