"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import type { AttributionData, ProductComment, ProductDetail } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { Icon, type IconName } from "@/components/shared/Icon";
import { Donut, KpiCard, ScoreRing, bayesScore100, hasEnoughBayesData } from "@/components/shared/MockVisuals";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { AspectRadarChart } from "@/components/charts/AspectRadarChart";
import { AreaChart } from "@/components/charts/AreaChart";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CustomSelect } from "@/components/ui/custom-select";
import { calculateControversyLabel } from "@/lib/utils";
import { Modal } from "@/components/admin/Modal";
import { Input } from "@/components/ui/input";

type Section = "analytics" | "specs" | "timeline" | "comments";

const baseSections: Array<{ id: Section; label: string; icon: IconName }> = [
  { id: "analytics", label: "Phân tích", icon: "activity" },
  { id: "specs", label: "Thông số kỹ thuật", icon: "spec" },
  { id: "timeline", label: "Dòng thời gian", icon: "clock" },
];

const SPEC_FALLBACK_INFO: Record<string, { label: string; unit?: string }> = {
  screen_technology: { label: "Công nghệ màn hình" },
  screen_size_inches: { label: "Kích thước màn hình", unit: "inch" },
  ram_gb: { label: "Dung lượng RAM", unit: "GB" },
  storage_gb: { label: "Bộ nhớ trong", unit: "GB" },
  battery_mah: { label: "Dung lượng pin", unit: "mAh" },
  chipset: { label: "Vi xử lý (Chipset)" },
  generation: { label: "Thế hệ" },
  release_date: { label: "Ngày ra mắt" },
  model_year: { label: "Năm model" },
  processor: { label: "Bộ vi xử lý (CPU)" },
  graphics: { label: "Card đồ họa (GPU)" },
  battery_hours: { label: "Thời lượng pin", unit: "giờ" },
  connection: { label: "Kết nối" },
  connector: { label: "Cổng sạc" },
  noise_cancellation: { label: "Chống ồn chủ động (ANC)" },
};

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [data, setData] = useState<ProductDetail | null>(null);
  const [attribution, setAttribution] = useState<AttributionData | null>(null);
  const [comments, setComments] = useState<ProductComment[]>([]);
  const [section, setSection] = useState<Section>("analytics");
  const [loading, setLoading] = useState(true);
  const [isFavorite, setIsFavorite] = useState(false);
  const [favoriteLoading, setFavoriteLoading] = useState(false);
  const [proposalSent, setProposalSent] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editDescription, setEditDescription] = useState("");
  const [editOfficialUrl, setEditOfficialUrl] = useState("");
  const [editImageUrl, setEditImageUrl] = useState("");
  const [editSpecs, setEditSpecs] = useState<Record<string, any>>({});

  const aspectOptions = useMemo(() => {
    if (data?.spec_templates?.length) {
      return data.spec_templates.map(t => ({ value: t.spec_key, label: t.display_label }));
    }
    return [
      { value: "performance", label: "Hiệu năng" },
      { value: "design", label: "Thiết kế" },
      { value: "screen", label: "Màn hình" },
      { value: "battery", label: "Pin" },
      { value: "camera", label: "Camera" },
      { value: "features", label: "Tính năng" },
    ];
  }, [data]);

  useEffect(() => {
    if (!id) return;
    Promise.all([api.products.aspects(id), api.products.attribution(id).catch(() => null), api.products.comments(id).catch(() => [])]).then(([detail, timeline, productComments]) => { setData(detail); setAttribution(timeline); setComments(productComments); }).finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id || !user) {
      setIsFavorite(false);
      return;
    }
    let active = true;
    api.products.favorites
      .status(id)
      .then((status) => {
        if (active) setIsFavorite(status.is_favorite);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [id, user]);

  useEffect(() => {
    if (editModalOpen && data) {
      setEditDescription(data.details?.description ?? "");
      setEditOfficialUrl(data.details?.official_url ?? "");
      setEditImageUrl(data.details?.image_url ?? "");
      
      const initialSpecs: Record<string, any> = {};
      if (data.spec_templates) {
        data.spec_templates.forEach(t => {
          const currentValue = data.details?.specs?.[t.spec_key];
          initialSpecs[t.spec_key] = currentValue !== undefined ? String(currentValue) : "";
        });
      }
      setEditSpecs(initialSpecs);
    }
  }, [editModalOpen, data]);

  const sentiment = useMemo(() => {
    if (!data?.aspects.length) return { positive: 0, negative: 0, neutral: 100 };
    const positive = data.aspects.reduce((sum, item) => sum + item.positive_pct, 0) / data.aspects.length;
    const negative = data.aspects.reduce((sum, item) => sum + item.negative_pct, 0) / data.aspects.length;
    return { positive, negative, neutral: Math.max(0, 100 - positive - negative) };
  }, [data]);

  const controversyLabel = useMemo(() => {
    return calculateControversyLabel(sentiment.positive, sentiment.negative);
  }, [sentiment]);

  const [timeRange, setTimeRange] = useState<"7d" | "15d" | "30d" | "3m" | "6m" | "1y">("30d");

  const now = useMemo(() => {
    if (attribution?.trend?.length) {
      return new Date(attribution.trend[attribution.trend.length - 1].date);
    }
    return new Date();
  }, [attribution]);

  const filteredTrend = useMemo(() => {
    if (!attribution?.trend?.length) return [];
    const limitDate = new Date(now);
    if (timeRange === "7d") limitDate.setDate(now.getDate() - 7);
    else if (timeRange === "15d") limitDate.setDate(now.getDate() - 15);
    else if (timeRange === "30d") limitDate.setDate(now.getDate() - 30);
    else if (timeRange === "3m") limitDate.setMonth(now.getMonth() - 3);
    else if (timeRange === "6m") limitDate.setMonth(now.getMonth() - 6);
    else if (timeRange === "1y") limitDate.setFullYear(now.getFullYear() - 1);
    
    return attribution.trend.filter(t => new Date(t.date) >= limitDate);
  }, [attribution, timeRange, now]);

  const filteredEvents = useMemo(() => {
    if (!attribution?.events?.length) return [];
    const limitDate = new Date(now);
    if (timeRange === "7d") limitDate.setDate(now.getDate() - 7);
    else if (timeRange === "15d") limitDate.setDate(now.getDate() - 15);
    else if (timeRange === "30d") limitDate.setDate(now.getDate() - 30);
    else if (timeRange === "3m") limitDate.setMonth(now.getMonth() - 3);
    else if (timeRange === "6m") limitDate.setMonth(now.getMonth() - 6);
    else if (timeRange === "1y") limitDate.setFullYear(now.getFullYear() - 1);
    
    return attribution.events.filter(e => new Date(e.change_point_date) >= limitDate);
  }, [attribution, timeRange, now]);

  const chartMarkers = useMemo(() => {
    if (!filteredTrend.length || !filteredEvents.length) return [];
    return filteredEvents
      .map((event) => {
        const idx = filteredTrend.findIndex((t) => t.date === event.change_point_date);
        if (idx !== -1) {
          return {
            index: idx,
            direction: event.sentiment_direction,
          };
        }
        return null;
      })
      .filter((m): m is { index: number; direction: "POSITIVE" | "NEGATIVE" } => m !== null);
  }, [filteredTrend, filteredEvents]);

  const chartSeries = useMemo(() => {
    return filteredTrend.map((t, index) => {
      const dateObj = new Date(t.date);
      const dateStr = dateObj.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
      
      let label = "";
      const len = filteredTrend.length;
      
      if (timeRange === "7d") {
        label = dateStr;
      } else if (timeRange === "15d") {
        if (index % 2 === 0 || index === len - 1) label = dateStr;
      } else if (timeRange === "30d") {
        if (index % 7 === 0 || index === len - 1) label = dateStr;
      } else if (timeRange === "3m") {
        if (index % 14 === 0 || index === len - 1) label = dateStr;
      } else if (timeRange === "6m") {
        if (index % 21 === 0 || index === len - 1) label = dateStr;
      } else if (timeRange === "1y") {
        const prevDate = index > 0 ? new Date(filteredTrend[index - 1].date) : null;
        if (!prevDate || dateObj.getMonth() !== prevDate.getMonth() || index === len - 1) {
          label = `T${dateObj.getMonth() + 1}`;
        }
      }
      
      return {
        label,
        value: t.sentiment_score
      };
    });
  }, [filteredTrend, timeRange]);

  if (loading) return <div className="grid min-h-[400px] place-items-center"><div className="spinner" /></div>;
  if (!data || data.total_mentions === 0 || data.statement_count === 0) return <div className="mx-auto max-w-5xl p-8"><Link href="/" className="muted">← Quay lại danh sách</Link><div className="card mt-6 p-10 text-center">Sản phẩm này sẽ được cập nhật thêm trong tương lai. Vui lòng quay lại sau!</div></div>;
  const specs = data.details?.specs ?? {};
  const sections = [...baseSections, { id: "comments" as const, label: `Bình luận (${comments.length})`, icon: "bell" as const }];

  async function submitProposal() {
    if (!id || !data) return;
    try {
      const proposed_specs: Record<string, any> = {};
      
      if (data?.spec_templates) {
        for (const t of data.spec_templates) {
          const rawValue = editSpecs[t.spec_key];
          if (rawValue === undefined) continue;
          
          let finalValue: any = String(rawValue).trim();
          if (t.value_type === "number") {
            if (finalValue === "") {
              finalValue = undefined;
            } else {
              finalValue = Number(finalValue);
              if (isNaN(finalValue)) {
                alert(`Thông số "${t.display_label}" yêu cầu nhập số hợp lệ.`);
                return;
              }
            }
          } else if (t.value_type === "boolean") {
            if (finalValue === "") {
              finalValue = undefined;
            } else {
              const lower = String(finalValue).toLowerCase();
              finalValue = lower === "true" || lower === "1" || lower === "có" || lower === "yes";
            }
          } else {
            if (finalValue === "") {
              finalValue = undefined;
            }
          }

          // Check if different from the original value
          const originalValue = data.details?.specs?.[t.spec_key];
          const isOriginalEmpty = originalValue === undefined || originalValue === null || originalValue === "";
          const isProposedEmpty = finalValue === undefined || finalValue === null || finalValue === "";
          
          if (isOriginalEmpty && isProposedEmpty) {
            continue;
          }
          
          if (originalValue === finalValue) {
            continue;
          }
          
          proposed_specs[t.spec_key] = finalValue === undefined ? null : finalValue;
        }
      }

      const origDesc = data.details?.description ?? "";
      const proposedDesc = editDescription.trim();
      const descriptionToSend = proposedDesc !== origDesc ? proposedDesc : undefined;

      const origUrl = data.details?.official_url ?? "";
      const proposedUrl = editOfficialUrl.trim();
      const officialUrlToSend = proposedUrl !== origUrl ? proposedUrl : undefined;

      const origImg = data.details?.image_url ?? "";
      const proposedImg = editImageUrl.trim();
      const imageUrlToSend = proposedImg !== origImg ? proposedImg : undefined;

      const dataToSend = {
        proposed_specs: Object.keys(proposed_specs).length > 0 ? proposed_specs : undefined,
        proposed_description: descriptionToSend,
        proposed_official_url: officialUrlToSend,
        proposed_image_url: imageUrlToSend,
      };

      if (!dataToSend.proposed_specs && !dataToSend.proposed_description && !dataToSend.proposed_official_url && !dataToSend.proposed_image_url) {
        alert("Bạn chưa thay đổi thông tin nào so với thông số hiện tại.");
        return;
      }

      await api.products.submitDetails(id, dataToSend);
      setProposalSent(true);
      setEditModalOpen(false);
    } catch (e) {
      console.error(e);
      alert("Lỗi khi gửi đề xuất. Vui lòng thử lại.");
    }
  }

  async function toggleFavorite() {
    if (!id) return;
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(`/product/${id}`)}`);
      return;
    }
    setFavoriteLoading(true);
    try {
      const status = isFavorite
        ? await api.products.favorites.remove(id)
        : await api.products.favorites.add(id);
      setIsFavorite(status.is_favorite);
    } finally {
      setFavoriteLoading(false);
    }
  }

  return (
    <main className="fade-in mx-auto max-w-[1120px] px-6 py-7 pb-20">
      <Link href="/" className="muted mb-[18px] inline-flex items-center gap-1.5 text-sm font-semibold hover:text-[var(--primary)]"><Icon name="chevron" size={16} style={{ transform: "rotate(90deg)" }} />Quay lại danh sách</Link>
      <section className="card mb-[18px] p-[26px]">
        <div className="flex flex-wrap justify-between gap-6"><div className="min-w-0 flex-[1_1_320px]"><div className="mb-2.5 flex flex-wrap gap-2"><span className="chip brand">{data.category}</span><span className="chip">{data.brand}</span><span className={`chip ${controversyLabel === "high" ? "neg" : controversyLabel === "medium" ? "neu" : "pos"}`}>{controversyLabel === "high" ? "Nhiều tranh cãi" : controversyLabel === "medium" ? "Tranh cãi vừa" : "Ít tranh cãi"}</span></div><h1 className="m-0 text-[32px] font-extrabold tracking-[-.02em]">{data.product_name}</h1><p className="muted mt-2 max-w-xl text-[14.5px] leading-relaxed">{data.details?.description ?? "Phân tích cảm xúc cộng đồng dựa trên bình luận YouTube Việt Nam."}</p><div className="mt-4 flex flex-wrap gap-2.5"><Button variant="outline" onClick={toggleFavorite} disabled={favoriteLoading}><Icon name={isFavorite ? "heartSolid" : "heart"} size={16} className={isFavorite ? "text-[var(--neg)]" : ""} />{isFavorite ? "Đã lưu" : "Lưu sản phẩm"}</Button>{data.details?.official_url && <a href={data.details.official_url} target="_blank" rel="noreferrer"><Button variant="outline"><Icon name="external" size={16} />Trang chính thức</Button></a>}</div></div><div className="flex min-w-48 flex-col items-center gap-3"><ScoreRing score={data.bayesian_score} statementCount={data.statement_count} size={104} /><div className="text-center"><div className="num text-[15px] font-bold">{data.total_mentions.toLocaleString("vi-VN")}</div><div className="faint text-xs">lượt đề cập đã phân tích</div>{!hasEnoughBayesData(data.statement_count) && <div className="faint mt-1 text-xs font-semibold">Chưa đủ dữ liệu Bayes</div>}</div></div></div>
        <div className="mt-[18px]"><SentimentBar positivePct={sentiment.positive} negativePct={sentiment.negative} height={12} /><div className="mt-2 flex justify-between text-[13px] font-semibold"><span className="text-[var(--pos)]">{sentiment.positive.toFixed(0)}% hài lòng</span><span className="text-[var(--neu)]">{sentiment.neutral.toFixed(0)}% trung lập</span><span className="text-[var(--neg)]">{sentiment.negative.toFixed(0)}% bất mãn</span></div></div>
      </section>

      <nav className="sticky top-[72px] z-20 mb-[18px] flex flex-wrap gap-1.5 rounded-[14px] border border-[var(--border)] bg-[var(--nav-bg)] p-1.5 backdrop-blur-xl">{sections.map((item) => <button key={item.id} onClick={() => setSection(item.id)} className={`flex items-center gap-1.5 rounded-[9px] px-[15px] py-2.5 text-sm font-semibold transition-all ${section === item.id ? "bg-[var(--primary)] text-[var(--on-primary)]" : "text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}><Icon name={item.icon} size={16} />{item.label}</button>)}</nav>

      {section === "analytics" && (
        <div className="fade-in flex flex-col gap-[18px]">
          <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3.5">
            <KpiCard
              icon="gauge"
              label="Điểm tín nhiệm"
              value={hasEnoughBayesData(data.statement_count) ? bayesScore100(data.bayesian_score).toFixed(1) : "Chưa đủ dữ liệu"}
              sub="trên thang 0-100"
            />
            <KpiCard
              icon="heart"
              label="Tỉ lệ hài lòng"
              value={`${sentiment.positive.toFixed(0)}%`}
              accent="var(--pos)"
            />
            <KpiCard
              icon="bell"
              label="Tổng đề cập"
              value={data.total_mentions < 1000 ? data.total_mentions.toLocaleString("vi-VN") : `${(data.total_mentions / 1000).toFixed(1)}K`}
              sub="12 tháng gần nhất"
              accent="var(--v-400)"
            />
            <KpiCard
              icon="activity"
              label="Mức tranh cãi"
              value={controversyLabel === "high" ? "Cao" : controversyLabel === "medium" ? "Vừa" : "Thấp"}
              accent="var(--neu)"
            />
          </div>

          <div className="analytics-grid grid grid-cols-[1.1fr_.9fr] gap-[18px]">
            <div className="card p-[22px]">
              <h3 className="text-[16.5px] font-bold">Đánh giá theo 6 khía cạnh</h3>
              <p className="faint mb-2 text-[13px]">Tỉ lệ cảm xúc hài lòng ở từng khía cạnh sản phẩm.</p>
              <AspectRadarChart aspects={data.aspects} />
            </div>

            <div className="card flex flex-col p-[22px]">
              <h3 className="mb-4 text-[16.5px] font-bold">Phân bổ cảm xúc</h3>
              <div className="mb-3.5 grid place-items-center">
                <Donut positive={sentiment.positive} neutral={sentiment.neutral} negative={sentiment.negative} />
              </div>
              {[
                ["Hài lòng", sentiment.positive, "var(--pos)"],
                ["Trung lập", sentiment.neutral, "var(--neu)"],
                ["Bất mãn", sentiment.negative, "var(--neg)"],
              ].map(([label, value, color]) => (
                <div key={String(label)} className="flex items-center gap-2.5 py-1">
                  <span className="h-2.5 w-2.5 rounded-[3px]" style={{ background: String(color) }} />
                  <span className="flex-1 text-[13.5px] font-semibold">{label}</span>
                  <span className="num font-bold">{Number(value).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card p-[22px]">
            <h3 className="mb-4 text-[16.5px] font-bold">Chi tiết theo khía cạnh</h3>
            <div className="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4">
              {data.aspects.map((a) => {
                const neutralPct = Math.max(0, 100 - a.positive_pct - a.negative_pct);
                return (
                  <div key={a.aspect_label} className="flex flex-col gap-1.5">
                    <div className="flex justify-between text-[13.5px]">
                      <span className="font-bold">{a.aspect_label}</span>
                      <span className="faint num">{a.total_mentions.toLocaleString("vi-VN")} đề cập</span>
                    </div>
                    <SentimentBar
                      positivePct={a.positive_pct}
                      negativePct={a.negative_pct}
                      neutralPct={neutralPct}
                      height={8}
                    />
                    <div className="flex justify-between text-[11.5px] font-semibold">
                      <span className="text-[var(--pos)]">{a.positive_pct.toFixed(1)}%</span>
                      <span className="text-[var(--neg)]">{a.negative_pct.toFixed(1)}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
      {section === "specs" && (
        <div className="analytics-grid fade-in grid grid-cols-[1.4fr_1fr] gap-[18px]">
          <div className="card p-[22px]">
            <h3 className="text-[16.5px] font-bold">Thông số thiết bị</h3>
            <p className="faint mb-4 text-[13px]">Thông tin kỹ thuật chính thức của {data.product_name}.</p>
            <dl className="grid grid-cols-2">
              {Object.entries(specs).map(([key, value]) => {
                const template = data.spec_templates?.find(t => t.spec_key === key);
                const fallback = SPEC_FALLBACK_INFO[key];
                
                const label = template?.display_label || fallback?.label || key;
                const unitName = template?.unit || fallback?.unit || "";
                const unit = unitName ? ` ${unitName}` : "";
                
                let displayVal = String(value);
                if (value === true) displayVal = "Có";
                else if (value === false) displayVal = "Không";
                return (
                  <div key={key} className="border-b border-[var(--border)] px-1 py-[13px]">
                    <dt className="faint mb-1 text-xs font-semibold">{label}</dt>
                    <dd className="m-0 text-[14.5px] font-bold">{displayVal}{unit}</dd>
                  </div>
                );
              })}
            </dl>
          </div>
          <div className="card bg-[var(--primary-soft)] p-[22px] flex flex-col justify-between">
            <div>
              <h3 className="text-[16.5px] font-bold text-[var(--primary)]">Đóng góp thông tin</h3>
              <p className="muted mt-1.5 text-[13.5px] leading-relaxed">
                Bạn phát hiện thông tin kỹ thuật hoặc mô tả của sản phẩm này chưa chính xác hoặc còn thiếu? Hãy đóng góp ý kiến chỉnh sửa để quản trị viên kiểm duyệt.
              </p>
            </div>
            <div className="mt-5">
              {user ? (
                proposalSent ? (
                  <div className="flex gap-2.5 rounded-xl bg-[var(--surface)] p-3.5 text-sm">
                    <Icon name="check" size={22} style={{ color: "var(--pos)" }} />
                    <div>
                      <div className="font-bold">Đã gửi đề xuất</div>
                      <div className="faint text-xs">Đang chờ quản trị viên duyệt.</div>
                    </div>
                  </div>
                ) : (
                  <Button onClick={() => setEditModalOpen(true)} className="w-full">
                    <Icon name="plus" size={16} className="mr-1.5" />
                    Đề xuất chỉnh sửa thông tin
                  </Button>
                )
              ) : (
                <div className="text-center py-2">
                  <p className="muted mb-3.5 text-[13.5px]">Đăng nhập để gửi đề xuất bổ sung thông số sản phẩm.</p>
                  <Link href={`/login?next=${encodeURIComponent(`/product/${id}`)}`}><Button className="w-full">Đăng nhập</Button></Link>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {section === "timeline" && (
        <div className="fade-in flex flex-col gap-[18px]">
          {filteredTrend?.length ? (
            <div className="card p-[22px]">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-[16.5px] font-bold m-0">Biểu đồ xu hướng cảm xúc theo thời gian</h3>
                <div className="flex gap-1 rounded-lg bg-[var(--surface-3)] p-1">
                  {(["7d", "15d", "30d", "3m", "6m", "1y"] as const).map((r) => (
                    <button
                      key={r}
                      onClick={() => setTimeRange(r)}
                      className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
                        timeRange === r ? "bg-[var(--primary)] text-white shadow-sm" : "text-[var(--text-3)] hover:text-[var(--text-1)]"
                      }`}
                    >
                      {r === "7d" ? "7 ngày" : r === "15d" ? "15 ngày" : r === "30d" ? "30 ngày" : r === "3m" ? "3 tháng" : r === "6m" ? "6 tháng" : "1 năm"}
                    </button>
                  ))}
                </div>
              </div>
              <AreaChart
                series={chartSeries}
                markers={chartMarkers}
              />
            </div>
          ) : (
            <div className="card p-[22px]">
              <h3 className="text-[16.5px] font-bold">Dòng thời gian quy kết (PELT)</h3>
              <p className="faint mt-1 text-[13px]">Chưa tích lũy đủ dữ liệu chuỗi thời gian cảm xúc.</p>
            </div>
          )}
          <div className="card p-[22px]">
            <h3 className="mb-[18px] text-[16.5px] font-bold">Sự kiện ảnh hưởng cảm xúc</h3>
            {filteredEvents?.length ? (
              <div className="relative ml-2 border-l-2 border-[var(--border)] pl-5">
                {filteredEvents.map((event) => (
                  <div key={`${event.change_point_date}-${event.event_video_title}`} className="relative pb-5">
                    <span
                      className="absolute -left-[31px] top-0 grid h-5 w-5 place-items-center rounded-full text-white"
                      style={{ background: event.sentiment_direction === "POSITIVE" ? "var(--pos)" : "var(--neg)" }}
                    >
                      <Icon name={event.sentiment_direction === "POSITIVE" ? "arrowUp" : "arrowDown"} size={12} />
                    </span>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="num faint text-xs">{event.change_point_date}</span>
                      <span className={`chip ${event.sentiment_direction === "POSITIVE" ? "pos" : "neg"}`}>
                        {event.sentiment_direction === "POSITIVE" ? "Hài lòng ↑" : "Bất mãn ↓"}
                      </span>
                    </div>
                    <div className="mt-1 text-sm font-bold">{event.event_video_title}</div>
                    <p className="muted mt-1 text-[13.5px]">{event.explanation_text}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="faint py-8 text-center">Chưa đủ dữ liệu phân tích biến động.</div>
            )}
          </div>
        </div>
      )}
      {section === "comments" && (comments.length ? <div className="comments-grid fade-in grid grid-cols-3 gap-4">{[["POSITIVE", "Hài lòng", "pos", "var(--pos)"], ["NEGATIVE", "Bất mãn", "neg", "var(--neg)"], ["NEUTRAL", "Trung lập", "neu", "var(--neu)"]].map(([sentiment, label, cls, color]) => <div key={sentiment} className="flex flex-col gap-3"><div className="flex items-center gap-2"><span className="h-[9px] w-[9px] rounded-full" style={{ background: color }} /><h3 className="text-[15.5px] font-bold">{label}</h3><span className="faint text-xs">({comments.filter((item) => item.sentiment_label === sentiment).length})</span></div>{comments.filter((item) => item.sentiment_label === sentiment).map((item) => <div key={`${item.comment_id}-${item.aspect_label}-${item.text}`} className="card p-4" style={{ borderLeft: `3px solid ${color}` }}><div className="mb-2 flex items-center justify-between"><div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-full bg-[var(--surface-3)] text-xs font-bold">{item.author.charAt(0)}</span><span className="text-[13px] font-bold">{item.author}</span></div><span className={`chip ${cls}`}>{item.aspect_label}</span></div><p className="m-0 text-[13.5px] leading-relaxed">&ldquo;{item.text}&rdquo;</p><div className="faint mt-2.5 flex items-center gap-1 text-[11.5px]"><Icon name="spark" size={12} />Độ tin cậy mô hình: <b className="num" style={{ color }}>{(item.confidence_score * 100).toFixed(0)}%</b></div></div>)}</div>)}</div> : <div className="card faint p-10 text-center">Chưa có bình luận đã phân tích cho sản phẩm này.</div>)}

      {/* Modal đề xuất chỉnh sửa hoàn chỉnh của User */}
      <Modal open={editModalOpen} title="Đề xuất chỉnh sửa thông tin sản phẩm" onClose={() => setEditModalOpen(false)} size="2xl">
        <div className="space-y-5 p-1 max-h-[75vh] overflow-y-auto pr-2">
          <p className="text-sm text-[var(--text-3)] leading-relaxed m-0">
            Các thay đổi của bạn sẽ được quản trị viên duyệt trước khi cập nhật chính thức vào hệ thống.
          </p>

          {/* Mô tả & URL */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider mb-2">Thông tin chung</h4>
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-xs font-bold text-[var(--text-2)]">Mô tả sản phẩm</label>
                <Textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Nhập mô tả tóm tắt về sản phẩm..."
                  className="min-h-[80px] text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1.5 block text-xs font-bold text-[var(--text-2)]">Đường dẫn chính thức</label>
                  <Input
                    value={editOfficialUrl}
                    onChange={(e) => setEditOfficialUrl(e.target.value)}
                    placeholder="https://example.com/product"
                    className="text-sm"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-bold text-[var(--text-2)]">Ảnh sản phẩm (URL)</label>
                  <Input
                    value={editImageUrl}
                    onChange={(e) => setEditImageUrl(e.target.value)}
                    placeholder="https://example.com/image.jpg"
                    className="text-sm"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-[var(--border)] my-4" />

          {/* Thông số kỹ thuật */}
          <div className="space-y-4">
            <h4 className="text-xs font-bold text-[var(--primary)] uppercase tracking-wider mb-2">Thông số kỹ thuật</h4>
            {data.spec_templates && data.spec_templates.length > 0 ? (
              <div className="grid grid-cols-2 gap-4">
                {data.spec_templates.map((t) => (
                  <div key={t.spec_key} className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-[var(--text-2)]">
                      {t.display_label} {t.unit ? `(${t.unit})` : ""}
                    </label>
                    {t.value_type === "boolean" ? (
                      <CustomSelect
                        value={String(editSpecs[t.spec_key] ?? "")}
                        onChange={(val) => setEditSpecs((prev) => ({ ...prev, [t.spec_key]: val }))}
                        options={[
                          { value: "", label: "Chọn..." },
                          { value: "true", label: "Có" },
                          { value: "false", label: "Không" }
                        ]}
                      />
                    ) : (
                      <Input
                        type={t.value_type === "number" ? "number" : "text"}
                        value={editSpecs[t.spec_key] ?? ""}
                        onChange={(e) => setEditSpecs((prev) => ({ ...prev, [t.spec_key]: e.target.value }))}
                        placeholder={`Nhập ${t.display_label.toLowerCase()}...`}
                        className="text-sm"
                      />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-[var(--text-3)] text-center py-4 bg-[var(--surface-2)] rounded-lg">
                Danh mục này chưa cấu hình template thông số.
              </div>
            )}
          </div>

          {/* Nút bấm */}
          <div className="flex justify-end gap-3 pt-4 border-t border-[var(--border)] mt-6">
            <Button variant="outline" onClick={() => setEditModalOpen(false)}>Hủy</Button>
            <Button onClick={submitProposal}>Gửi đề xuất</Button>
          </div>
        </div>
      </Modal>
    </main>
  );
}
