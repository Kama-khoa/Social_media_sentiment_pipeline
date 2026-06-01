"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";
import type { AttributionData, CausalEventSummary } from "@/lib/types";
import { AttributionTimeline } from "@/components/charts/AttributionTimeline";

function formatViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toLocaleString();
}

function CausalEventCard({ event }: { event: CausalEventSummary }) {
  const isPositive = event.sentiment_direction === "POSITIVE";
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
      <div className="flex items-start gap-3">
        <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-lg ${
          isPositive ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400"
        }`}>
          {isPositive ? "↑" : "↓"}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-slate-500">{event.change_point_date}</span>
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
              isPositive
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
                : "bg-rose-500/15 text-rose-400 border border-rose-500/25"
            }`}>
              {isPositive ? "Tích cực" : "Tiêu cực"}
            </span>
          </div>
          <div className="mt-1.5 text-sm font-medium text-slate-200 line-clamp-2">
            {event.event_video_title}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {formatViews(event.event_view_count)} lượt xem
          </div>
          {event.explanation_text && (
            <div className="mt-2 text-xs text-slate-400 border-l-2 border-slate-600 pl-3">
              {event.explanation_text}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AttributionSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="h-4 bg-slate-700 rounded animate-pulse w-32" />
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
        <div className="h-4 bg-slate-700 rounded animate-pulse w-40 mb-4" />
        <div className="h-56 bg-slate-700 rounded animate-pulse" />
      </div>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
          <div className="flex gap-3">
            <div className="w-8 h-8 bg-slate-700 rounded-full animate-pulse shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="h-3 bg-slate-700 rounded animate-pulse w-24" />
              <div className="h-4 bg-slate-700 rounded animate-pulse w-3/4" />
              <div className="h-3 bg-slate-700 rounded animate-pulse w-20" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AttributionPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<AttributionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.products
      .attribution(id)
      .then(setData)
      .catch(() => setError("Không thể tải dữ liệu phân tích biến động."))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <AttributionSkeleton />;

  const backHref = `/analytics/products/${id}`;

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <Link href={backHref} className="text-slate-400 hover:text-cyan-400 text-sm transition-colors">
          ← Chi tiết sản phẩm
        </Link>
        <div className="mt-8 text-center py-16 text-slate-500">
          <div className="text-4xl mb-3">⚠</div>
          <div className="text-slate-400">{error ?? "Không tìm thấy dữ liệu."}</div>
        </div>
      </div>
    );
  }

  const hasEvents = data.events.length > 0;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <Link href={backHref} className="inline-flex items-center gap-1.5 text-slate-400 hover:text-cyan-400 text-sm transition-colors">
        ← Chi tiết sản phẩm
      </Link>

      <div>
        <h1 className="text-2xl font-bold text-slate-100">Phân tích biến động sentiment</h1>
        <p className="text-slate-400 text-sm mt-1">{data.product_name}</p>
      </div>

      {!hasEvents ? (
        <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-12 text-center">
          <div className="text-4xl mb-3 text-slate-600">📊</div>
          <div className="text-slate-400 font-medium">Chưa có đủ dữ liệu để phân tích biến động</div>
          <div className="text-slate-500 text-sm mt-1">
            Cần thu thập thêm bình luận qua nhiều ngày để phát hiện điểm thay đổi.
          </div>
        </div>
      ) : (
        <>
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
                Timeline biến động
              </h2>
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-3 h-0.5 bg-emerald-500" />
                  Tích cực
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-3 h-0.5 bg-rose-500" />
                  Tiêu cực
                </span>
              </div>
            </div>
            <AttributionTimeline events={data.events} />
          </div>

          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              Sự kiện gây biến động ({data.events.length})
            </h2>
            {data.events.map((event, i) => (
              <CausalEventCard key={`${event.change_point_date}-${i}`} event={event} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
