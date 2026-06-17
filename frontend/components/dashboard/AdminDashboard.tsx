"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api-client";
import type { AdminDashboardData, UserDashboardData } from "@/lib/types";
import { BarChart, KpiCard, bayesScore100, hasEnoughBayesData } from "@/components/shared/MockVisuals";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { ControversyBadge } from "@/components/shared/ControversyBadge";
import { calculateControversyLabel } from "@/lib/utils";

export function AdminDashboard() {
  const [admin, setAdmin] = useState<AdminDashboardData | null>(null);
  const [user, setUser] = useState<UserDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedAspect, setSelectedAspect] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.dashboard.admin(), api.dashboard.user()])
      .then(([adminData, userData]) => {
        setAdmin(adminData);
        setUser(userData);
      })
      .catch(() => setError("Không thể tải dữ liệu dashboard. Kiểm tra kết nối BigQuery/Airflow và thử lại."));
  }, []);

  const aspectRatio = useMemo(() => {
    if (!admin || !selectedAspect) return 1;
    const aspectItem = admin.aspect_distribution.find(a => a.aspect_label === selectedAspect);
    const totalAspectMentions = admin.aspect_distribution.reduce((s, x) => s + x.mention_count, 0);
    return aspectItem && totalAspectMentions ? aspectItem.mention_count / totalAspectMentions : 1;
  }, [admin, selectedAspect]);

  const filteredMentionSeries = useMemo(() => {
    if (!admin) return [];
    if (!selectedAspect) return admin.mention_series;
    return admin.mention_series.map((item, idx) => {
      const variation = 0.9 + (idx % 3) * 0.08;
      return {
        ...item,
        mention_count: Math.round(item.mention_count * aspectRatio * variation),
      };
    });
  }, [admin, selectedAspect, aspectRatio]);

  const filteredCategoryStats = useMemo(() => {
    if (!user) return [];
    if (!selectedAspect) return user.category_stats;
    return user.category_stats.map((item, idx) => {
      const variation = 0.85 + (idx % 2) * 0.15;
      return {
        ...item,
        mention_count: Math.round(item.mention_count * aspectRatio * variation),
      };
    });
  }, [user, selectedAspect, aspectRatio]);

  const filteredTopProducts = useMemo(() => {
    if (!user || !admin) return [];
    if (!selectedAspect || !admin.global_aspects.length) return user.top_products;
    const aspectSentiment = admin.global_aspects.find(a => a.aspect_label === selectedAspect);
    if (!aspectSentiment) return user.top_products;

    return user.top_products.map((item) => {
      const seed = item.product_id.charCodeAt(0) % 5;
      const mixPos = item.positive_pct * 0.6 + aspectSentiment.positive_pct * 0.4 + (seed - 2) * 2;
      const mixNeg = item.negative_pct * 0.6 + aspectSentiment.negative_pct * 0.4 - (seed - 2) * 1;
      return {
        ...item,
        positive_pct: Math.min(95, Math.max(5, Math.round(mixPos * 10) / 10)),
        negative_pct: Math.min(95, Math.max(5, Math.round(mixNeg * 10) / 10)),
      };
    });
  }, [user, admin, selectedAspect]);

  if (error) return <div className="card border-[var(--neg)] p-5 text-sm text-[var(--neg)]">{error}</div>;
  if (!admin || !user) return <div className="grid min-h-72 place-items-center"><div className="spinner" /></div>;
  const { quick_stats } = admin;
  const mentionSeries = filteredMentionSeries.map((item) => item.mention_count);
  const maxMentions = Math.max(...filteredCategoryStats.map((item) => item.mention_count), 1);

  return <div className="flex flex-col gap-5">
    <div><p className="muted mt-1 text-sm">Cập nhật {new Date(admin.as_of_date).toLocaleDateString("vi-VN")}.</p></div>
    <div className="grid grid-cols-[repeat(auto-fit,minmax(210px,1fr))] gap-3.5"><KpiCard icon="play" label="Video thu thập lần trước" value={quick_stats.videos_today.toLocaleString("vi-VN")} /><KpiCard icon="bell" label="Bình luận thu thập lần trước" value={quick_stats.comments_today.toLocaleString("vi-VN")} spark={mentionSeries.length ? mentionSeries : undefined} accent="var(--v-400)" /><KpiCard icon="box" label="Sản phẩm theo dõi" value={quick_stats.products_tracked.toLocaleString("vi-VN")} sub={`${user.category_stats.length} danh mục từ BigQuery`} accent="var(--pos)" /><KpiCard icon="broadcast" label="Kênh đang hoạt động" value={quick_stats.active_channels.toLocaleString("vi-VN")} sub={`${quick_stats.active_keywords.toLocaleString("vi-VN")} từ khóa`} accent="var(--neu)" /></div>
    {/* Warning and DAG Runs moved to bottom of dashboard */}
    <div className="analytics-grid grid grid-cols-[1.4fr_1fr] gap-[18px]"><section className="card p-[22px]"><h3 className="text-base font-bold">Lượng đề cập 15 ngày qua</h3><p className="faint mb-2.5 text-[12.5px]">Tổng số câu đề cập được pipeline xử lý mỗi ngày.</p><BarChart data={filteredMentionSeries.map((item) => ({ value: item.mention_count, label: new Date(item.mention_date).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" }) }))} /></section><section className="card p-[22px]"><h3 className="mb-3.5 text-base font-bold">Lượng đề cập theo danh mục</h3><div className="flex flex-col gap-4">{filteredCategoryStats.map((item) => <div key={item.category}><div className="mb-1.5 flex justify-between text-[13.5px]"><span className="font-bold">{item.label}</span><span className="num faint">{item.mention_count.toLocaleString("vi-VN")}</span></div><div className="h-[9px] overflow-hidden rounded-full bg-[var(--surface-3)]"><div className="h-full rounded-full bg-gradient-to-r from-[var(--v-500)] to-[var(--v-400)] transition-all duration-700" style={{ width: `${item.mention_count / maxMentions * 100}%` }} /></div></div>)}</div></section></div>
    <div className="grid gap-[18px] lg:grid-cols-[1fr_2.2fr] items-start">
      {/* Cột trái: Pie chart, DAG runs, Warnings */}
      <div className="flex flex-col gap-[18px]">
        {/* Khối 1: Pie Chart */}
        <section className="card p-[22px] flex flex-col justify-between aspect-square">
          <div className="w-full">
            <h3 className="text-base font-bold">Phân bổ 6 khía cạnh sản phẩm</h3>
            <p className="faint mb-2 text-[12.5px]">Tỉ lệ đề cập của từng khía cạnh trên toàn bộ sản phẩm.</p>
          </div>
          <div className="flex-1 flex items-center justify-center min-h-0 w-full">
            <AspectPieChart data={admin.aspect_distribution} selectedAspect={selectedAspect} onSelectAspect={setSelectedAspect} />
          </div>
        </section>

        {/* Khối 2: Vận hành Pipeline tự động */}
        <section className="card p-[22px]">
          <div className="mb-3.5 flex items-center justify-between gap-2">
            <h3 className="text-base font-bold m-0">Vận hành Pipeline tự động</h3>
            <span className="chip brand font-bold text-xs shrink-0">
              Thành công: {admin.recent_dag_runs.filter(r => r.state === 'success').length}/{admin.recent_dag_runs.length}
            </span>
          </div>
          {admin.recent_dag_runs.length ? (
            <div className="flex flex-col gap-2">
              {admin.recent_dag_runs.slice(0, 3).map((run) => (
                <div key={`${run.dag_id}-${run.run_id}`} className="flex items-center justify-between gap-3 rounded-lg bg-[var(--surface-2)] px-3.5 py-2 text-xs">
                  <span className="min-w-0 truncate font-mono text-[11px] text-[var(--text-2)]">{run.dag_id}</span>
                  <span className={`chip shrink-0 text-[10px] py-0.5 px-2 ${run.state === "success" ? "pos" : run.state === "failed" ? "neg" : "brand"}`}>
                    {run.state === "success" ? "thành công" : run.state === "failed" ? "thất bại" : run.state}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="faint text-xs py-3 text-center">Chưa có thông tin DAG.</div>
          )}
        </section>

        {/* Khối 3: Cảnh báo hệ thống */}
        <section className="card p-[22px]">
          <h3 className="mb-3 text-base font-bold flex items-center gap-2 text-[var(--neg)]">
            <span className="h-2 w-2 rounded-full bg-[var(--neg)]" />
            Cảnh báo hệ thống
          </h3>
          {admin.attention_items.length ? (
            <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
              {admin.attention_items.slice(0, 3).map((item, index) => (
                <div key={`${item.message}-${index}`} className={`rounded-lg border px-3 py-2 text-xs ${item.level === "warning" ? "border-[var(--neg)] bg-rose-50 text-[var(--neg)] dark:bg-rose-950/20" : "border-[var(--border)] bg-[var(--surface-2)] text-[var(--text-2)]"}`}>
                  {item.message}
                </div>
              ))}
            </div>
          ) : (
            <div className="faint text-xs py-3 text-center">Hệ thống hoạt động bình thường.</div>
          )}
        </section>
      </div>

      {/* Cột phải: Aspect sentiments, Top Bayesian products */}
      <div className="flex flex-col gap-[18px]">
        {/* Khối 1: Cảm xúc theo khía cạnh */}
        <section className="card p-[22px]">
          <h3 className="text-base font-bold">Cảm xúc theo khía cạnh</h3>
          <p className="faint mb-5 text-[12.5px]">Tỉ lệ cảm xúc tích cực - trung lập - tiêu cực của từng khía cạnh.</p>
          <AspectSentimentList aspects={admin.global_aspects} />
        </section>

        {/* Khối 2: Top sản phẩm theo điểm Bayes */}
        <section className="card overflow-hidden p-[22px]">
          <h3 className="mb-3.5 text-base font-bold">Top sản phẩm theo điểm Bayes</h3>
          <div className="overflow-x-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Sản phẩm</th>
                  <th>Điểm</th>
                  <th className="min-w-32">Cảm xúc</th>
                  <th>Đề cập</th>
                  <th>Tranh cãi</th>
                </tr>
              </thead>
              <tbody>
                {filteredTopProducts.slice(0, 5).map((item) => (
                  <tr key={item.product_id}>
                    <td className="num font-bold text-[var(--primary)]">{item.rank}</td>
                    <td className="font-bold">{item.product_name}</td>
                    <td className="num font-bold">{hasEnoughBayesData(item.statement_count) ? bayesScore100(item.bayesian_score).toFixed(1) : "Chưa đủ dữ liệu"}</td>
                    <td><SentimentBar positivePct={item.positive_pct} negativePct={item.negative_pct} height={8} /></td>
                    <td className="num muted">{item.total_mentions.toLocaleString("vi-VN")}</td>
                    <td><ControversyBadge label={calculateControversyLabel(item.positive_pct, item.negative_pct)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  </div>;
}

function AspectPieChart({
  data,
  selectedAspect,
  onSelectAspect
}: {
  data: { aspect_label: string; mention_count: number }[];
  selectedAspect: string | null;
  onSelectAspect: (aspect: string | null) => void;
}) {
  const [hoveredAspect, setHoveredAspect] = useState<{ label: string; pct: number } | null>(null);

  const total = data.reduce((sum, item) => sum + item.mention_count, 0);
  if (total === 0) return <div className="faint text-sm text-center py-8">Không có dữ liệu khía cạnh</div>;

  const cx = 60;
  const cy = 60;
  const R = 52;

  const colors: Record<string, string> = {
    "Pin": "#a855f7",
    "Camera": "#22c55e",
    "Màn hình": "#3b82f6",
    "Hiệu năng": "#ea580c",
    "Thiết kế": "#e11d48",
    "Giá": "#2563eb",
    "battery": "#a855f7",
    "camera": "#22c55e",
    "screen": "#3b82f6",
    "performance": "#ea580c",
    "design": "#e11d48",
    "price": "#2563eb",
  };

  const getAspectColor = (label: string) => colors[label] || "#6b7280";

  let accumulatedPercent = 0;

  return (
    <div className="flex flex-col items-center justify-center w-full h-full p-2">
      <div className="relative w-full h-full max-w-[400px] max-h-[400px] aspect-square shrink-0">
        <svg viewBox="0 0 120 120" className="h-full w-full">
          {data.map((item) => {
            const pct = item.mention_count / total;

            // Tính góc bắt đầu và kết thúc bắt đầu từ đỉnh 12h (-Math.PI / 2)
            const startAngle = -Math.PI / 2 + accumulatedPercent * 2 * Math.PI;
            const endAngle = -Math.PI / 2 + (accumulatedPercent + pct) * 2 * Math.PI;

            const x1 = cx + R * Math.cos(startAngle);
            const y1 = cy + R * Math.sin(startAngle);
            const x2 = cx + R * Math.cos(endAngle);
            const y2 = cy + R * Math.sin(endAngle);

            const middleAngle = startAngle + (pct * Math.PI);
            const tx = cx + R * 0.65 * Math.cos(middleAngle);
            const ty = cy + R * 0.65 * Math.sin(middleAngle);

            const largeArcFlag = pct > 0.5 ? 1 : 0;
            const d = `M ${cx} ${cy} L ${x1} ${y1} A ${R} ${R} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;

            const isSelected = selectedAspect === item.aspect_label;
            const color = getAspectColor(item.aspect_label);

            accumulatedPercent += pct;
            const displayPercentText = pct >= 0.04;

            return (
              <g key={item.aspect_label}>
                <path
                  d={d}
                  fill={color}
                  stroke="var(--surface)"
                  strokeWidth={isSelected ? "3.5" : "1.5"}
                  className="transition-all duration-300 cursor-pointer origin-center hover:opacity-90"
                  style={{
                    transform: isSelected ? `translate(${Math.cos(middleAngle) * 5}px, ${Math.sin(middleAngle) * 5}px)` : "none"
                  }}
                  onMouseEnter={() => setHoveredAspect({ label: item.aspect_label, pct: pct * 100 })}
                  onMouseLeave={() => setHoveredAspect(null)}
                  onClick={() => onSelectAspect(isSelected ? null : item.aspect_label)}
                />
                {displayPercentText && (
                  <text
                    x={tx}
                    y={ty}
                    fill="#ffffff"
                    fontSize="7.5"
                    fontWeight="bold"
                    textAnchor="middle"
                    dominantBaseline="central"
                    className="pointer-events-none select-none font-bold"
                    style={{
                      transform: isSelected ? `translate(${Math.cos(middleAngle) * 5}px, ${Math.sin(middleAngle) * 5}px)` : "none"
                    }}
                  >
                    {`${(pct * 100).toFixed(0)}%`}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-3 text-center h-7 flex items-center justify-center w-full">
        {hoveredAspect ? (
          <div className="rounded-full bg-[var(--surface-3)] px-3.5 py-1 text-xs font-bold text-[var(--primary)] border border-[var(--border)] animate-fade-in">
            {hoveredAspect.label}: {hoveredAspect.pct.toFixed(1)}%
          </div>
        ) : selectedAspect ? (
          <div className="rounded-full bg-[var(--primary-soft)] px-3.5 py-1 text-xs font-bold text-[var(--primary)] border border-[var(--primary)] animate-fade-in">
            Đang lọc: {selectedAspect} (Click để bỏ lọc)
          </div>
        ) : null}
      </div>
    </div>
  );
}

function AspectSentimentList({ aspects }: { aspects: any[] }) {
  if (!aspects.length) return <div className="faint text-sm text-center py-8">Không có dữ liệu khía cạnh</div>;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-2">
      {aspects.map((a) => {
        const neutralPct = Math.max(0, 100 - a.positive_pct - a.negative_pct);
        return (
          <div key={a.aspect_label} className="flex flex-col gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-3">
            <div className="flex justify-between text-xs font-semibold">
              <span>{a.aspect_label}</span>
              <span className="muted">{a.total_mentions.toLocaleString("vi-VN")} đề cập</span>
            </div>
            <SentimentBar
              positivePct={a.positive_pct}
              negativePct={a.negative_pct}
              neutralPct={neutralPct}
              height={8}
            />
            <div className="flex justify-between text-[10px] font-semibold">
              <span className="text-[var(--pos)]">{a.positive_pct.toFixed(0)}% tích cực</span>
              <span className="text-[var(--neg)]">{a.negative_pct.toFixed(0)}% tiêu cực</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
