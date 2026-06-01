"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { AdminDashboardData, DagRunSummary } from "@/lib/types";

function HealthDot({ status }: { status: "healthy" | "unhealthy" | "unknown" }) {
  const map = {
    healthy: "bg-emerald-500",
    unhealthy: "bg-rose-500",
    unknown: "bg-slate-400",
  };
  return <span className={`w-2 h-2 rounded-full ${map[status]} inline-block`} />;
}

function ServiceCard({ title, status, subtitle }: { title: string; status: "healthy" | "unhealthy" | "unknown"; subtitle?: string }) {
  const textMap = { healthy: "text-emerald-700", unhealthy: "text-rose-700", unknown: "text-slate-500" };
  const bgMap = { healthy: "bg-emerald-50 border-emerald-200", unhealthy: "bg-rose-50 border-rose-200", unknown: "bg-slate-50 border-slate-200" };
  const labelMap = { healthy: "Hoạt động", unhealthy: "Lỗi", unknown: "Không xác định" };

  return (
    <div className={`rounded-xl border p-4 ${bgMap[status]}`}>
      <div className="flex items-center gap-2 mb-1">
        <HealthDot status={status} />
        <span className={`text-xs font-semibold uppercase tracking-wider ${textMap[status]}`}>{labelMap[status]}</span>
      </div>
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function QuotaBar({ used, limit }: { used: number; limit: number }) {
  const pct = Math.min((used / limit) * 100, 100);
  const color = pct > 80 ? "bg-rose-400" : pct > 50 ? "bg-amber-400" : "bg-indigo-400";
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-500 mb-1.5">
        <span>Đã dùng: <strong className="text-slate-700">{used.toLocaleString("vi-VN")}</strong> units</span>
        <span>Giới hạn: {limit.toLocaleString("vi-VN")}</span>
      </div>
      <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-400 mt-1">{pct.toFixed(0)}% — còn {(limit - used).toLocaleString("vi-VN")} units</p>
    </div>
  );
}

function DagStateChip({ state }: { state: DagRunSummary["state"] }) {
  const map = {
    success: "bg-emerald-50 border-emerald-200 text-emerald-700",
    failed: "bg-rose-50 border-rose-200 text-rose-700",
    running: "bg-blue-50 border-blue-200 text-blue-700",
    queued: "bg-slate-100 border-slate-200 text-slate-600",
  };
  const labelMap = { success: "Thành công", failed: "Thất bại", running: "Đang chạy", queued: "Chờ" };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${map[state]}`}>
      {state === "running" && <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />}
      {labelMap[state]}
    </span>
  );
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function formatDagId(dagId: string): string {
  return dagId.replace(/_dag$/, "").split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

export function AdminDashboard() {
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.dashboard
      .admin()
      .then(setData)
      .catch(() => setError("Không thể tải dữ liệu pipeline"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 h-20 animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2 bg-white rounded-xl border border-slate-200 p-4 h-48 animate-pulse" />
          <div className="bg-white rounded-xl border border-slate-200 p-4 h-48 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-rose-700 text-sm">{error || "Lỗi không xác định"}</div>
    );
  }

  const { pipeline_status, quick_stats, recent_dag_runs, attention_items, as_of_date } = data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Tổng quan hệ thống</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Cập nhật: {new Date(as_of_date).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })}
          </p>
        </div>
        <button className="flex items-center gap-1.5 px-3 py-2 bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium rounded-lg transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Trigger DAG
        </button>
      </div>

      {/* Pipeline status cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <ServiceCard title="Airflow Webserver" status={pipeline_status.airflow_webserver} />
        <ServiceCard title="Airflow Scheduler" status={pipeline_status.airflow_scheduler} />
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 font-medium mb-2">Quota YouTube hôm nay</p>
          <QuotaBar used={pipeline_status.quota_used_today} limit={pipeline_status.quota_limit} />
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 font-medium mb-1">NLP Batch gần nhất</p>
          {pipeline_status.last_nlp_batch_run_id ? (
            <>
              <p className="text-xs font-medium text-slate-700 truncate" title={pipeline_status.last_nlp_batch_run_id}>
                {pipeline_status.last_nlp_batch_run_id.split("T")[0]}
              </p>
              {pipeline_status.nlp_fallback_pct !== null && (
                <p className="text-xs text-slate-500 mt-0.5">Fallback Gemini: <strong className="text-slate-700">{pipeline_status.nlp_fallback_pct.toFixed(1)}%</strong></p>
              )}
            </>
          ) : (
            <p className="text-xs text-slate-400">Chưa có</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* DAG Runs */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-700">DAG runs gần nhất</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">DAG</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Trạng thái</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Thời gian</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-slate-400">Thời điểm</th>
              </tr>
            </thead>
            <tbody>
              {recent_dag_runs.map((run) => (
                <tr key={run.run_id} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3.5">
                    <p className="font-medium text-slate-700 text-xs">{formatDagId(run.dag_id)}</p>
                    <p className="text-xs text-slate-400 font-mono truncate max-w-[160px]" title={run.run_id}>{run.run_id.split("__")[0]}</p>
                  </td>
                  <td className="px-5 py-3.5">
                    <DagStateChip state={run.state} />
                  </td>
                  <td className="px-5 py-3.5 text-xs text-slate-600">{formatDuration(run.duration_seconds)}</td>
                  <td className="px-5 py-3.5 text-xs text-slate-400">
                    {run.start_date ? new Date(run.start_date).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Quick stats */}
        <div className="space-y-3">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Dữ liệu hôm nay</h3>
            <div className="space-y-2.5">
              {[
                { label: "Video mới", value: quick_stats.videos_today },
                { label: "Bình luận mới", value: quick_stats.comments_today.toLocaleString("vi-VN") },
                { label: "Sản phẩm tracked", value: quick_stats.products_tracked },
                { label: "Kênh hoạt động", value: quick_stats.active_channels },
                { label: "Từ khóa hoạt động", value: quick_stats.active_keywords },
              ].map((s) => (
                <div key={s.label} className="flex justify-between items-center">
                  <span className="text-xs text-slate-500">{s.label}</span>
                  <span className="text-xs font-semibold text-slate-700">{s.value}</span>
                </div>
              ))}
            </div>
          </div>

          {attention_items.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Cần chú ý</h3>
              <div className="space-y-2">
                {attention_items.map((item, i) => (
                  <div key={i} className={`flex gap-2 p-2.5 rounded-lg text-xs ${
                    item.level === "warning" ? "bg-amber-50 border border-amber-200" : "bg-slate-50 border border-slate-200"
                  }`}>
                    <svg className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${item.level === "warning" ? "text-amber-600" : "text-slate-500"}`} fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d={item.level === "warning"
                        ? "M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        : "M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                      } clipRule="evenodd" />
                    </svg>
                    <span className={item.level === "warning" ? "text-amber-700" : "text-slate-600"}>{item.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
