"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { PipelineHealthData } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";

const DAG_IDS = [
  { id: "youtube_daily_extraction_dag", label: "Thu thập video hằng ngày" },
  { id: "sentiment_analysis_dag", label: "Phân tích NLP" },
  { id: "seed_sync_dag", label: "Đồng bộ seed data" },
];

function HealthDot({ status }: { status: string }) {
  const isHealthy = status === "healthy";
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${
      isHealthy ? "text-emerald-600" : "text-rose-600"
    }`}>
      <span className={`w-2 h-2 rounded-full ${isHealthy ? "bg-emerald-500" : "bg-rose-500"}`} />
      {isHealthy ? "Healthy" : status}
    </span>
  );
}

function DagRunBadge({ state }: { state: string }) {
  const config: Record<string, string> = {
    success: "bg-emerald-100 text-emerald-700",
    failed: "bg-rose-100 text-rose-700",
    running: "bg-blue-100 text-blue-700",
    queued: "bg-amber-100 text-amber-700",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
      config[state] ?? "bg-slate-100 text-slate-600"
    }`}>
      {state === "running" && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mr-1.5 animate-pulse" />}
      {state}
    </span>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-slate-800 mt-1">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function QuotaBar({ used, limit }: { used: number; limit: number }) {
  const pct = Math.min((used / limit) * 100, 100);
  const color = pct > 80 ? "bg-rose-500" : pct > 60 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Quota hôm nay</p>
        <span className="text-xs text-slate-500">{used.toLocaleString()} / {limit.toLocaleString()}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-400 mt-1.5">{pct.toFixed(1)}% đã dùng</p>
    </div>
  );
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export default function PipelineHealthPage() {
  const [data, setData] = useState<PipelineHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggerDagId, setTriggerDagId] = useState(DAG_IDS[0].id);
  const [confirmTrigger, setConfirmTrigger] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [triggerResult, setTriggerResult] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setData(await api.admin.pipeline.health());
    } catch (err: unknown) {
      const e = err as { status?: number };
      if (e?.status === 502) {
        setError("Không thể kết nối tới Airflow. Kiểm tra xem Airflow có đang chạy không.");
      } else {
        setError("Không thể tải dữ liệu pipeline. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleTrigger() {
    setTriggering(true);
    try {
      const result = await api.admin.pipeline.trigger(triggerDagId) as { run_id?: string };
      setTriggerResult(`Đã trigger thành công. Run ID: ${result?.run_id ?? "unknown"}`);
      setConfirmTrigger(false);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setTriggerResult(`Lỗi: ${e?.detail ?? "Không thể trigger DAG."}`);
      setConfirmTrigger(false);
    } finally {
      setTriggering(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-6 bg-slate-200 rounded animate-pulse w-48" />
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-slate-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Vận hành Pipeline</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {data ? `Cập nhật lúc ${new Date(data.as_of).toLocaleTimeString("vi-VN")}` : ""}
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Làm mới
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl px-4 py-4">
          <strong>Lỗi kết nối:</strong> {error}
        </div>
      )}

      {data && (
        <>
          {/* Airflow status */}
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">Trạng thái Airflow</h2>
            <div className="flex items-center gap-8">
              <div>
                <p className="text-xs text-slate-500 mb-1">Webserver</p>
                <HealthDot status={data.airflow.webserver} />
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-1">Scheduler</p>
                <HealthDot status={data.airflow.scheduler} />
              </div>
            </div>
          </div>

          {/* Metrics grid */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <QuotaBar used={data.metrics.quota_used_today} limit={data.metrics.quota_limit} />
            <MetricCard
              label="Video thu thập hôm nay"
              value={data.metrics.videos_crawled_today.toLocaleString()}
            />
            <MetricCard
              label="Bình luận thu thập hôm nay"
              value={data.metrics.comments_crawled_today.toLocaleString()}
            />
            <MetricCard
              label="Kênh chờ historical scan"
              value={data.metrics.channels_pending_historical}
              sub="Cần chạy Phase B"
            />
            <MetricCard
              label="NLP batch cuối"
              value={data.metrics.last_nlp_batch_id ? "Đã chạy" : "Chưa có"}
              sub={data.metrics.last_nlp_batch_id ?? "—"}
            />
          </div>

          {/* DAG runs table */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">DAG Runs gần đây</h2>
            </div>
            {data.recent_dag_runs.length === 0 ? (
              <div className="px-5 py-10 text-center text-slate-400 text-sm">
                Không có DAG run nào gần đây
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">DAG</th>
                    <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Run ID</th>
                    <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Trạng thái</th>
                    <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Bắt đầu</th>
                    <th className="px-4 py-3 text-right text-xs text-slate-500 font-medium uppercase tracking-wider">Thời gian</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_dag_runs.map((run) => (
                    <tr key={run.run_id} className="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                      <td className="px-4 py-3.5">
                        <span className="text-xs font-mono text-slate-600">{run.dag_id}</span>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="text-xs font-mono text-slate-400 truncate max-w-[160px] block">{run.run_id}</span>
                      </td>
                      <td className="px-4 py-3.5"><DagRunBadge state={run.state} /></td>
                      <td className="px-4 py-3.5 text-xs text-slate-400">
                        {run.start_date ? new Date(run.start_date).toLocaleString("vi-VN") : "—"}
                      </td>
                      <td className="px-4 py-3.5 text-right text-xs text-slate-400">
                        {formatDuration(run.duration_seconds)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Trigger section */}
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">Trigger thủ công</h2>

            {triggerResult && (
              <div className={`mb-4 text-sm rounded-lg px-4 py-3 ${
                triggerResult.startsWith("Lỗi")
                  ? "bg-rose-50 border border-rose-200 text-rose-700"
                  : "bg-emerald-50 border border-emerald-200 text-emerald-700"
              }`}>
                {triggerResult}
              </div>
            )}

            <div className="flex items-center gap-3">
              <select
                value={triggerDagId}
                onChange={(e) => setTriggerDagId(e.target.value)}
                className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30"
              >
                {DAG_IDS.map((d) => (
                  <option key={d.id} value={d.id}>{d.label} ({d.id})</option>
                ))}
              </select>
              <button
                onClick={() => { setTriggerResult(null); setConfirmTrigger(true); }}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 3l14 9-14 9V3z" />
                </svg>
                Trigger DAG
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Trigger sẽ tạo một DAG run mới ngay lập tức. Chỉ nên dùng khi cần chạy thủ công ngoài lịch.
            </p>
          </div>
        </>
      )}

      {/* Confirm trigger dialog */}
      <Modal
        open={confirmTrigger}
        title="Xác nhận Trigger DAG"
        onClose={() => setConfirmTrigger(false)}
      >
        <div className="space-y-5">
          <div>
            <p className="text-sm text-slate-600">Bạn sắp trigger DAG:</p>
            <p className="mt-2 font-mono text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-800">
              {triggerDagId}
            </p>
            <p className="text-xs text-slate-400 mt-2">
              DAG sẽ chạy ngay lập tức, song song với các run đang có nếu có.
            </p>
          </div>
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setConfirmTrigger(false)}
              className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Hủy
            </button>
            <button
              onClick={handleTrigger}
              disabled={triggering}
              className="px-4 py-2 text-sm bg-violet-600 hover:bg-violet-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
            >
              {triggering ? "Đang trigger…" : "Xác nhận Trigger"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
