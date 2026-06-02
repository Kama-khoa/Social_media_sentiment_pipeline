"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { AdminDashboardData, UserDashboardData } from "@/lib/types";
import { BarChart, KpiCard } from "@/components/shared/MockVisuals";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { ControversyBadge } from "@/components/shared/ControversyBadge";

export function AdminDashboard() {
  const [admin, setAdmin] = useState<AdminDashboardData | null>(null);
  const [user, setUser] = useState<UserDashboardData | null>(null);

  useEffect(() => { Promise.all([api.dashboard.admin(), api.dashboard.user()]).then(([adminData, userData]) => { setAdmin(adminData); setUser(userData); }); }, []);
  if (!admin || !user) return <div className="grid min-h-72 place-items-center"><div className="spinner" /></div>;
  const { quick_stats } = admin;
  const mentionSeries = admin.mention_series.map((item) => item.mention_count);
  const maxMentions = Math.max(...user.category_stats.map((item) => item.mention_count), 1);

  return <div className="flex flex-col gap-5">
    <div><h2 className="text-[22px] font-extrabold tracking-[-.01em]">Tổng quan phân tích</h2><p className="muted mt-1 text-sm">Bức tranh toàn cảnh dữ liệu cảm xúc & vận hành hệ thống, cập nhật {new Date(admin.as_of_date).toLocaleDateString("vi-VN")}.</p></div>
    <div className="grid grid-cols-[repeat(auto-fit,minmax(210px,1fr))] gap-3.5"><KpiCard icon="play" label="Video thu thập hôm nay" value={quick_stats.videos_today} /><KpiCard icon="bell" label="Bình luận thu thập hôm nay" value={`${(quick_stats.comments_today / 1000).toFixed(1)}K`} spark={mentionSeries.length ? mentionSeries : undefined} accent="var(--v-400)" /><KpiCard icon="box" label="Sản phẩm theo dõi" value={quick_stats.products_tracked} sub={`${user.category_stats.length} danh mục từ BigQuery`} accent="var(--pos)" /><KpiCard icon="broadcast" label="Kênh đang hoạt động" value={quick_stats.active_channels} sub={`${quick_stats.active_keywords} từ khóa`} accent="var(--neu)" /></div>
    <div className="analytics-grid grid grid-cols-[1.4fr_1fr] gap-[18px]"><section className="card p-[22px]"><h3 className="text-base font-bold">Lượng đề cập 15 ngày qua</h3><p className="faint mb-2.5 text-[12.5px]">Tổng số câu đề cập được pipeline xử lý mỗi ngày.</p><BarChart data={admin.mention_series.map((item) => ({ value: item.mention_count, label: new Date(item.mention_date).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" }) }))} /></section><section className="card p-[22px]"><h3 className="mb-3.5 text-base font-bold">Đề cập theo danh mục</h3><div className="flex flex-col gap-4">{user.category_stats.map((item) => <div key={item.category}><div className="mb-1.5 flex justify-between text-[13.5px]"><span className="font-bold">{item.label}</span><span className="num faint">{item.mention_count.toLocaleString("vi-VN")}</span></div><div className="h-[9px] overflow-hidden rounded-full bg-[var(--surface-3)]"><div className="h-full rounded-full bg-gradient-to-r from-[var(--v-500)] to-[var(--v-400)] transition-all duration-700" style={{ width: `${item.mention_count / maxMentions * 100}%` }} /></div></div>)}</div></section></div>
    <section className="card overflow-hidden p-[22px]"><h3 className="mb-3.5 text-base font-bold">Top sản phẩm theo điểm Bayesian</h3><div className="overflow-x-auto"><table className="tbl"><thead><tr><th>#</th><th>Sản phẩm</th><th>Điểm</th><th className="min-w-32">Cảm xúc</th><th>Đề cập</th><th>Tranh cãi</th></tr></thead><tbody>{user.top_products.slice(0, 5).map((item) => <tr key={item.product_id}><td className="num font-bold text-[var(--primary)]">{item.rank}</td><td className="font-bold">{item.product_name}</td><td className="num font-bold">{(item.bayesian_score * 100).toFixed(1)}</td><td><SentimentBar positivePct={item.positive_pct} negativePct={item.negative_pct} height={8} /></td><td className="num muted">{item.total_mentions.toLocaleString("vi-VN")}</td><td><ControversyBadge label={item.controversy_label} /></td></tr>)}</tbody></table></div></section>
  </div>;
}
