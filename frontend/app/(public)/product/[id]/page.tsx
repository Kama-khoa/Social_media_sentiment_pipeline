"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api-client";
import type { AttributionData, ProductComment, ProductDetail } from "@/lib/types";
import { useAuth } from "@/lib/auth-context";
import { Icon, type IconName } from "@/components/shared/Icon";
import { Donut, KpiCard, ScoreRing, bayesScore100, hasEnoughBayesData } from "@/components/shared/MockVisuals";
import { SentimentBar } from "@/components/charts/SentimentBar";
import { AspectRadarChart } from "@/components/charts/AspectRadarChart";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type Section = "analytics" | "specs" | "timeline" | "comments";

const baseSections: Array<{ id: Section; label: string; icon: IconName }> = [
  { id: "analytics", label: "Phân tích", icon: "activity" },
  { id: "specs", label: "Thông số kỹ thuật", icon: "spec" },
  { id: "timeline", label: "Dòng thời gian", icon: "clock" },
];

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [data, setData] = useState<ProductDetail | null>(null);
  const [attribution, setAttribution] = useState<AttributionData | null>(null);
  const [comments, setComments] = useState<ProductComment[]>([]);
  const [section, setSection] = useState<Section>("analytics");
  const [loading, setLoading] = useState(true);
  const [proposal, setProposal] = useState("{}");
  const [proposalSent, setProposalSent] = useState(false);

  useEffect(() => {
    if (!id) return;
    Promise.all([api.products.aspects(id), api.products.attribution(id).catch(() => null), api.products.comments(id).catch(() => [])]).then(([detail, timeline, productComments]) => { setData(detail); setAttribution(timeline); setComments(productComments); }).finally(() => setLoading(false));
  }, [id]);

  const sentiment = useMemo(() => {
    if (!data?.aspects.length) return { positive: 0, negative: 0, neutral: 100 };
    const positive = data.aspects.reduce((sum, item) => sum + item.positive_pct, 0) / data.aspects.length;
    const negative = data.aspects.reduce((sum, item) => sum + item.negative_pct, 0) / data.aspects.length;
    return { positive, negative, neutral: Math.max(0, 100 - positive - negative) };
  }, [data]);

  if (loading) return <div className="grid min-h-[400px] place-items-center"><div className="spinner" /></div>;
  if (!data) return <div className="mx-auto max-w-5xl p-8"><Link href="/" className="muted">← Quay lại danh sách</Link><div className="card mt-6 p-10 text-center">Không tìm thấy sản phẩm.</div></div>;
  const specs = data.details?.specs ?? {};
  const sections = [...baseSections, { id: "comments" as const, label: `Bình luận (${comments.length})`, icon: "bell" as const }];

  async function submitProposal() {
    if (!id) return;
    const proposed_specs = JSON.parse(proposal) as Record<string, unknown>;
    await api.products.submitDetails(id, { proposed_specs });
    setProposalSent(true);
  }

  return (
    <main className="fade-in mx-auto max-w-[1120px] px-6 py-7 pb-20">
      <Link href="/" className="muted mb-[18px] inline-flex items-center gap-1.5 text-sm font-semibold hover:text-[var(--primary)]"><Icon name="chevron" size={16} style={{ transform: "rotate(90deg)" }} />Quay lại danh sách</Link>
      <section className="card mb-[18px] p-[26px]">
        <div className="flex flex-wrap justify-between gap-6"><div className="min-w-0 flex-[1_1_320px]"><div className="mb-2.5 flex flex-wrap gap-2"><span className="chip brand">{data.category}</span><span className="chip">{data.brand}</span><span className={`chip ${data.controversy_label === "high" ? "neg" : data.controversy_label === "medium" ? "neu" : "pos"}`}>{data.controversy_label === "high" ? "Nhiều tranh cãi" : data.controversy_label === "medium" ? "Tranh cãi vừa" : "Ít tranh cãi"}</span></div><h1 className="m-0 text-[32px] font-extrabold tracking-[-.02em]">{data.product_name}</h1><p className="muted mt-2 max-w-xl text-[14.5px] leading-relaxed">{data.details?.description ?? "Phân tích cảm xúc cộng đồng dựa trên bình luận YouTube Việt Nam."}</p><div className="mt-4 flex flex-wrap gap-2.5"><Button variant="secondary"><Icon name="heart" size={16} />Lưu sản phẩm</Button>{data.details?.official_url && <a href={data.details.official_url} target="_blank" rel="noreferrer"><Button variant="outline"><Icon name="external" size={16} />Trang chính thức</Button></a>}</div></div><div className="flex min-w-48 flex-col items-center gap-3"><ScoreRing score={data.bayesian_score} statementCount={data.statement_count} size={104} /><div className="text-center"><div className="num text-[15px] font-bold">{data.total_mentions.toLocaleString("vi-VN")}</div><div className="faint text-xs">lượt đề cập đã phân tích</div>{!hasEnoughBayesData(data.statement_count) && <div className="faint mt-1 text-xs font-semibold">Chưa đủ dữ liệu Bayes</div>}</div></div></div>
        <div className="mt-[18px]"><SentimentBar positivePct={sentiment.positive} negativePct={sentiment.negative} height={12} /><div className="mt-2 flex justify-between text-[13px] font-semibold"><span className="text-[var(--pos)]">{sentiment.positive.toFixed(0)}% tích cực</span><span className="text-[var(--neu)]">{sentiment.neutral.toFixed(0)}% trung lập</span><span className="text-[var(--neg)]">{sentiment.negative.toFixed(0)}% tiêu cực</span></div></div>
      </section>

      <nav className="sticky top-[72px] z-20 mb-[18px] flex flex-wrap gap-1.5 rounded-[14px] border border-[var(--border)] bg-[var(--nav-bg)] p-1.5 backdrop-blur-xl">{sections.map((item) => <button key={item.id} onClick={() => setSection(item.id)} className={`flex items-center gap-1.5 rounded-[9px] px-[15px] py-2.5 text-sm font-semibold transition-all ${section === item.id ? "bg-[var(--primary)] text-[var(--on-primary)]" : "text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}><Icon name={item.icon} size={16} />{item.label}</button>)}</nav>

      {section === "analytics" && <div className="fade-in flex flex-col gap-[18px]"><div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3.5"><KpiCard icon="gauge" label="Điểm Bayes" value={hasEnoughBayesData(data.statement_count) ? bayesScore100(data.bayesian_score).toFixed(1) : "Chưa đủ dữ liệu"} sub="trên thang 0-100" /><KpiCard icon="heart" label="Tỉ lệ tích cực" value={`${sentiment.positive.toFixed(0)}%`} accent="var(--pos)" /><KpiCard icon="bell" label="Tổng đề cập" value={`${(data.total_mentions / 1000).toFixed(1)}K`} sub={`${data.statement_count.toLocaleString("vi-VN")} câu đánh giá`} accent="var(--v-400)" /><KpiCard icon="activity" label="Mức tranh cãi" value={data.controversy_label === "high" ? "Cao" : data.controversy_label === "medium" ? "Vừa" : "Thấp"} accent="var(--neu)" /></div><div className="analytics-grid grid grid-cols-[1.1fr_.9fr] gap-[18px]"><div className="card p-[22px]"><h3 className="text-[16.5px] font-bold">Đánh giá theo 6 khía cạnh</h3><p className="faint mb-2 text-[13px]">Tỉ lệ cảm xúc tích cực ở từng khía cạnh sản phẩm.</p><AspectRadarChart aspects={data.aspects} /></div><div className="card flex flex-col p-[22px]"><h3 className="mb-4 text-[16.5px] font-bold">Phân bổ cảm xúc</h3><div className="mb-3.5 grid place-items-center"><Donut positive={sentiment.positive} neutral={sentiment.neutral} negative={sentiment.negative} /></div>{[["Tích cực", sentiment.positive, "var(--pos)"], ["Trung lập", sentiment.neutral, "var(--neu)"], ["Tiêu cực", sentiment.negative, "var(--neg)"]].map(([label, value, color]) => <div key={String(label)} className="flex items-center gap-2.5 py-1"><span className="h-2.5 w-2.5 rounded-[3px]" style={{ background: String(color) }} /><span className="flex-1 text-[13.5px] font-semibold">{label}</span><span className="num font-bold">{Number(value).toFixed(0)}%</span></div>)}</div></div></div>}
      {section === "specs" && <div className="analytics-grid fade-in grid grid-cols-[1.4fr_1fr] gap-[18px]"><div className="card p-[22px]"><h3 className="text-[16.5px] font-bold">Thông số thiết bị</h3><p className="faint mb-4 text-[13px]">Thông tin kỹ thuật chính thức của {data.product_name}.</p><dl className="grid grid-cols-2">{Object.entries(specs).map(([key, value]) => <div key={key} className="border-b border-[var(--border)] px-1 py-[13px]"><dt className="faint mb-1 text-xs font-semibold">{key}</dt><dd className="m-0 text-[14.5px] font-bold">{String(value)}</dd></div>)}</dl></div><div className="card bg-[var(--primary-soft)] p-[22px]"><h3 className="text-[16.5px] font-bold text-[var(--primary)]">Đề xuất bổ sung thông số</h3>{user ? proposalSent ? <div className="mt-2 flex gap-2.5 rounded-xl bg-[var(--surface)] p-3.5 text-sm"><Icon name="check" size={22} style={{ color: "var(--pos)" }} /><div><div className="font-bold">Đã gửi đề xuất</div><div className="faint text-xs">Đang chờ quản trị viên duyệt.</div></div></div> : <><p className="muted mt-1 text-[13.5px]">Bạn thấy thông số chưa chính xác? Gửi đề xuất chỉnh sửa để quản trị viên duyệt.</p><Textarea value={proposal} onChange={(event) => setProposal(event.target.value)} className="mt-2 font-mono" /><Button onClick={submitProposal} className="mt-2.5 w-full">Gửi đề xuất</Button></> : <div className="py-4 text-center"><p className="muted mb-3 text-[13.5px]">Đăng nhập để gửi đề xuất bổ sung thông số sản phẩm.</p><Link href="/login"><Button>Đăng nhập</Button></Link></div>}</div></div>}
      {section === "timeline" && <div className="fade-in flex flex-col gap-[18px]"><div className="card p-[22px]"><h3 className="text-[16.5px] font-bold">Dòng thời gian quy kết (PELT)</h3><p className="faint mt-1 text-[13px]">Danh sách bên dưới được đọc trực tiếp từ causal_events. API hiện chưa cung cấp time series điểm cảm xúc nên giao diện không dựng đường biểu đồ giả.</p></div><div className="card p-[22px]"><h3 className="mb-[18px] text-[16.5px] font-bold">Sự kiện ảnh hưởng cảm xúc</h3>{attribution?.events.length ? <div className="relative ml-2 border-l-2 border-[var(--border)] pl-5">{attribution.events.map((event) => <div key={`${event.change_point_date}-${event.event_video_title}`} className="relative pb-5"><span className="absolute -left-[31px] top-0 grid h-5 w-5 place-items-center rounded-full text-white" style={{ background: event.sentiment_direction === "POSITIVE" ? "var(--pos)" : "var(--neg)" }}><Icon name={event.sentiment_direction === "POSITIVE" ? "arrowUp" : "arrowDown"} size={12} /></span><div className="flex flex-wrap items-center gap-2"><span className="num faint text-xs">{event.change_point_date}</span><span className={`chip ${event.sentiment_direction === "POSITIVE" ? "pos" : "neg"}`}>{event.sentiment_direction === "POSITIVE" ? "Tích cực ↑" : "Tiêu cực ↓"}</span></div><div className="mt-1 text-sm font-bold">{event.event_video_title}</div><p className="muted mt-1 text-[13.5px]">{event.explanation_text}</p></div>)}</div> : <div className="faint py-8 text-center">Chưa đủ dữ liệu phân tích biến động.</div>}</div></div>}
      {section === "comments" && (comments.length ? <div className="comments-grid fade-in grid grid-cols-3 gap-4">{[["POSITIVE", "Tích cực", "pos", "var(--pos)"], ["NEGATIVE", "Tiêu cực", "neg", "var(--neg)"], ["NEUTRAL", "Trung lập", "neu", "var(--neu)"]].map(([sentiment, label, cls, color]) => <div key={sentiment} className="flex flex-col gap-3"><div className="flex items-center gap-2"><span className="h-[9px] w-[9px] rounded-full" style={{ background: color }} /><h3 className="text-[15.5px] font-bold">{label}</h3><span className="faint text-xs">({comments.filter((item) => item.sentiment_label === sentiment).length})</span></div>{comments.filter((item) => item.sentiment_label === sentiment).map((item) => <div key={`${item.comment_id}-${item.aspect_label}-${item.text}`} className="card p-4" style={{ borderLeft: `3px solid ${color}` }}><div className="mb-2 flex items-center justify-between"><div className="flex items-center gap-2"><span className="grid h-7 w-7 place-items-center rounded-full bg-[var(--surface-3)] text-xs font-bold">{item.author.charAt(0)}</span><span className="text-[13px] font-bold">{item.author}</span></div><span className={`chip ${cls}`}>{item.aspect_label}</span></div><p className="m-0 text-[13.5px] leading-relaxed">&ldquo;{item.text}&rdquo;</p><div className="faint mt-2.5 flex items-center gap-1 text-[11.5px]"><Icon name="spark" size={12} />Độ tin cậy mô hình: <b className="num" style={{ color }}>{(item.confidence_score * 100).toFixed(0)}%</b></div></div>)}</div>)}</div> : <div className="card faint p-10 text-center">Chưa có bình luận đã phân tích cho sản phẩm này.</div>)}
    </main>
  );
}
