"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { PipelineHealthData } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { PageHeader } from "@/components/shared/PageHeader";

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
  const config: Record<string, React.ComponentProps<typeof Badge>["variant"]> = {
    success: "success",
    failed: "destructive",
    running: "brand",
    queued: "warning",
  };
  return (
    <Badge variant={config[state] ?? "secondary"}>
      {state === "running" && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mr-1.5 animate-pulse" />}
      {state}
    </Badge>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card className="p-4 shadow-none">
      <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-slate-800 mt-1">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
    </Card>
  );
}

function QuotaBar({ used, limit }: { used: number; limit: number }) {
  const pct = Math.min((used / limit) * 100, 100);
  const color = pct > 80 ? "bg-rose-500" : pct > 60 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <Card className="p-4 shadow-none">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Quota hôm nay</p>
        <span className="text-xs text-slate-500">{used.toLocaleString()} / {limit.toLocaleString()}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-slate-400 mt-1.5">{pct.toFixed(1)}% đã dùng</p>
    </Card>
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
      <PageHeader
        title="Vận hành Pipeline"
        description={data ? `Cập nhật lúc ${new Date(data.as_of).toLocaleTimeString("vi-VN")}` : ""}
        action={<Button
          onClick={load}
          variant="outline"
          size="sm"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Làm mới
        </Button>}
      />

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl px-4 py-4">
          <strong>Lỗi kết nối:</strong> {error}
        </div>
      )}

      {data && (
        <>
          {/* Airflow status */}
          <Card className="p-5 shadow-none">
            <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider mb-4">Trạng thái Airflow</h2>
            {data.airflow.message && (
              <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {data.airflow.message}
              </div>
            )}
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
          </Card>

          {/* Metrics grid */}
          <div id="ops" className="grid grid-cols-2 lg:grid-cols-3 gap-4 scroll-mt-24">
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
          <Card id="runs" className="overflow-hidden shadow-none scroll-mt-24">
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
          </Card>

          {/* Trigger section */}
          <Card className="p-5 shadow-none">
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
              <Select
                value={triggerDagId}
                onChange={(e) => setTriggerDagId(e.target.value)}
                className="flex-1"
              >
                {DAG_IDS.map((d) => (
                  <option key={d.id} value={d.id}>{d.label} ({d.id})</option>
                ))}
              </Select>
              <Button
                onClick={() => { setTriggerResult(null); setConfirmTrigger(true); }}
                className="whitespace-nowrap bg-violet-600 hover:bg-violet-700"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 3l14 9-14 9V3z" />
                </svg>
                Trigger DAG
              </Button>
            </div>
            <p className="text-xs text-slate-400 mt-2">
              Trigger sẽ tạo một DAG run mới ngay lập tức. Chỉ nên dùng khi cần chạy thủ công ngoài lịch.
            </p>
          </Card>
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
            <Button
              onClick={() => setConfirmTrigger(false)}
              variant="outline"
            >
              Hủy
            </Button>
            <Button
              onClick={handleTrigger}
              disabled={triggering}
              className="bg-violet-600 hover:bg-violet-700"
            >
              {triggering ? "Đang trigger…" : "Xác nhận Trigger"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
