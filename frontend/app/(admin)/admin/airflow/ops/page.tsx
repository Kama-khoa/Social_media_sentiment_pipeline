"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api-client";
import type { PipelineOpsSeries } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function PipelineOpsPage() {
  const [series, setSeries] = useState<PipelineOpsSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const s = await api.admin.pipeline.series();
      setSeries(s);
    } catch (err: unknown) {
      const e = err as { status?: number; detail?: string };
      setError(e?.detail || "Không thể tải dữ liệu vận hành. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  // Formatting chart data
  const chartData = useMemo(() => {
    if (!series) return [];
    return series.ops_series.map((v, i) => ({
      day: `Ngày ${i + 1}`,
      ops: v / 100,
      nlp: series.nlp_series[i]
    }));
  }, [series]);

  if (loading && !series) {
    return (
      <div className="space-y-6">
        <div className="h-6 bg-slate-200 rounded animate-pulse w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
        <div className="h-64 bg-slate-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5 relative">
      <PageHeader
        title="Chỉ số vận hành"
        description="Thông lượng thu thập, độ trễ và độ chính xác mô hình NLP theo thời gian."
        action={
          <button onClick={load} className="text-[13.5px] font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-50 transition flex items-center gap-2">
            <Icon name="refresh" size={16} /> Làm mới
          </button>
        }
      />

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-[13.5px] rounded-xl p-4">
          <strong>Lỗi kết nối:</strong> {error}
        </div>
      )}

      {series && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[14px]">
            <Card className="p-5">
              <div className="text-slate-500 text-[12.5px] font-semibold mb-2.5">Video / ngày</div>
              <div className="text-[22px] font-bold text-violet-600 font-mono">{series.videos_today}</div>
            </Card>
            <Card className="p-5">
              <div className="text-slate-500 text-[12.5px] font-semibold mb-2.5">Bình luận / ngày</div>
              <div className="text-[22px] font-bold text-blue-500 font-mono">{(series.comments_today / 1000).toFixed(1)}K</div>
            </Card>
            <Card className="p-5">
              <div className="text-slate-500 text-[12.5px] font-semibold mb-2.5">Độ trễ pipeline</div>
              <div className="text-[22px] font-bold text-emerald-500 font-mono">{series.pipeline_latency}</div>
            </Card>
            <Card className="p-5">
              <div className="text-slate-500 text-[12.5px] font-semibold mb-2.5">Độ chính xác NLP</div>
              <div className="text-[22px] font-bold text-slate-700 font-mono">{series.nlp_accuracy}</div>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-[18px]">
            <Card className="p-6">
              <h3 className="m-0 mb-1 text-base font-bold">Thông lượng thu thập</h3>
              <p className="text-slate-500 text-[12.5px] mb-4">Số bình luận xử lý mỗi ngày (x100) · 15 ngày.</p>
              <div className="h-[240px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorOps" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} dy={10} />
                    <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12, border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Area type="monotone" dataKey="ops" stroke="#7c3aed" strokeWidth={3} fillOpacity={1} fill="url(#colorOps)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card className="p-6">
              <h3 className="m-0 mb-1 text-base font-bold">Độ chính xác mô hình NLP</h3>
              <p className="text-slate-500 text-[12.5px] mb-4">Tỉ lệ dự đoán đúng của PhoBERT / vELECTRA (%).</p>
              <div className="h-[240px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorNlp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} dy={10} />
                    <Tooltip contentStyle={{ borderRadius: 8, fontSize: 12, border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                    <Area type="monotone" dataKey="nlp" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorNlp)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
