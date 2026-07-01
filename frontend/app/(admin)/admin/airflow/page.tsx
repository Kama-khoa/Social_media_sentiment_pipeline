"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { PipelineHealthData } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";

const PIPELINE_DAGS = [
  { id: "youtube_daily_extraction_dag", label: "Thu thập video YouTube", desc: "ELT extract + dbt staging" },
  { id: "sentiment_analysis_dag", label: "Phân tích cảm xúc NLP", desc: "PhoBERT + vELECTRA batch" },
  { id: "analytics_dag", label: "Tính toán Analytics", desc: "Bayesian ranking + controversy" },
  { id: "seed_sync_dag", label: "Đồng bộ hạt giống", desc: "Đồng bộ catalog + metadata" },
];

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function stateChip(state: string) {
  const map: Record<string, [string, string, string]> = {
    success: ["Thành công", "bg-emerald-50 text-emerald-700 border-emerald-200", "bg-emerald-500"],
    running: ["Đang chạy", "bg-violet-50 text-violet-700 border-violet-200", "bg-violet-500 animate-pulse"],
    queued: ["Đang chờ", "bg-slate-50 text-slate-600 border-slate-200", "bg-slate-400"],
    failed: ["Thất bại", "bg-rose-50 text-rose-700 border-rose-200", "bg-rose-500"],
  };
  const [t, cls, dot] = map[state] || [state, "bg-slate-50 text-slate-600 border-slate-200", "bg-slate-400"];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-xs font-semibold ${cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {t}
    </span>
  );
}

export default function PipelineHealthPage() {
  const [data, setData] = useState<PipelineHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedDag, setSelectedDag] = useState(PIPELINE_DAGS[0].id);
  const [triggerStatus, setTriggerStatus] = useState<"loading" | "success" | "error" | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const h = await api.admin.pipeline.health();
      setData(h);
    } catch (err: unknown) {
      const e = err as { status?: number; detail?: string };
      if (e?.status === 502) {
        setError("Không thể kết nối tới Airflow. Kiểm tra xem Airflow có đang chạy không.");
      } else {
        setError(e?.detail || "Không thể tải dữ liệu pipeline. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function doTrigger() {
    setTriggerStatus("loading");
    try {
      await api.admin.pipeline.trigger(selectedDag);
      setTriggerStatus("success");
      setTimeout(() => setTriggerStatus(null), 4500);
      await load();
    } catch (err) {
      setTriggerStatus("error");
      setTimeout(() => setTriggerStatus(null), 4500);
    }
  }

  async function handleToggleSchedule(dagId: string, currentPaused: boolean) {
    try {
      await api.admin.pipeline.pauseDag(dagId, !currentPaused);
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      alert(e?.detail || "Không thể cập nhật trạng thái schedule của DAG.");
    }
  }

  async function handleCancelTask(taskId: string) {
    const run = data?.recent_dag_runs.find(r => r.dag_id === selectedDag);
    if (!run || !run.run_id) return;
    
    if (!confirm(`Bạn có chắc chắn muốn hủy (đánh dấu thất bại) task "${taskId}" không?`)) {
      return;
    }
    
    try {
      await api.admin.pipeline.updateTaskState(selectedDag, run.run_id, taskId, "failed");
      await load();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      alert(e?.detail || "Không thể hủy task.");
    }
  }

  const selectedInfo = PIPELINE_DAGS.find(d => d.id === selectedDag);

  if (loading && !data) {
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
        title="Tình trạng Pipeline"
        description="Giám sát sức khỏe Airflow, hạn ngạch API và batch NLP gần nhất."
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

      {data && (
        <>
          {/* KPI cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-[14px]">
            <Card className="p-5 shadow-sm border-slate-200 rounded-[14px]">
              <div className="text-slate-500 text-[12.5px] font-semibold mb-2.5">Airflow Webserver</div>
              <div className="flex items-center gap-2.5">
                <span className={`w-3 h-3 rounded-full ${data.airflow.webserver === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
                <span className="font-bold text-lg">{data.airflow.webserver === "healthy" ? "Hoạt động tốt" : "Có lỗi"}</span>
              </div>
            </Card>
            <Card className="p-5 shadow-sm border-slate-200 rounded-[14px]">
              <div className="text-slate-500 text-[12.5px] font-semibold mb-2.5">Airflow Scheduler</div>
              <div className="flex items-center gap-2.5">
                <span className={`w-3 h-3 rounded-full ${data.airflow.scheduler === "healthy" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
                <span className="font-bold text-lg">{data.airflow.scheduler === "healthy" ? "Hoạt động tốt" : "Có lỗi"}</span>
              </div>
            </Card>
            <Card className="p-5 shadow-sm border-slate-200 rounded-[14px]">
              <div className="text-slate-500 text-[12.5px] font-semibold mb-2.5">Quota DAG sử dụng gần nhất</div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-bold text-[22px] font-mono text-slate-900">{data.metrics.quota_used_today.toLocaleString("vi-VN")}</span>
                <span className="text-slate-400 text-[13.5px]">/ {data.metrics.quota_limit.toLocaleString("vi-VN")}</span>
              </div>
              <div className="h-2 rounded-full bg-indigo-50 mt-2.5 overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full"
                  style={{ width: `${Math.min(100, (data.metrics.quota_used_today / (data.metrics.quota_limit || 1)) * 100)}%` }}
                />
              </div>
            </Card>
            <Card className="p-5 shadow-sm border-slate-200 rounded-[14px]">
              <div className="text-slate-500 text-[12.5px] font-semibold mb-2.5">NLP Fallback Rate</div>
              <div className="font-bold text-[22px] font-mono text-emerald-500">
                {data.metrics.nlp_fallback_rate != null ? `${(data.metrics.nlp_fallback_rate * 100).toFixed(1)}%` : "—"}
              </div>
              <div className="text-slate-400 text-[12.5px] mt-1.5 truncate">
                {data.metrics.last_nlp_batch_id || "chưa có"}
              </div>
            </Card>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-[14px]">
            {/* DAG Trigger */}
            <Card className="p-[22px] shadow-sm border-slate-200 rounded-[14px]">
              <div className="mb-[18px]">
                <h3 className="m-0 text-base font-bold mb-1">Kích hoạt DAG thủ công</h3>
                <p className="text-slate-500 m-0 text-[12.5px]">Trigger một DAG run ngay lập tức qua Airflow REST API.</p>
              </div>
              <div className="flex flex-col gap-[14px]">
                <div className="flex flex-col gap-2">
                  {PIPELINE_DAGS.map(d => {
                    const runDetail = data?.recent_dag_runs?.find(r => r.dag_id === d.id);
                    const isPaused = runDetail?.is_paused ?? false;
                    return (
                      <label key={d.id} onClick={() => setSelectedDag(d.id)} className={`flex items-center gap-3.5 p-3 px-4 rounded-[11px] cursor-pointer transition-all border ${selectedDag === d.id ? "bg-violet-50 border-violet-600" : "bg-slate-50 border-transparent hover:bg-slate-100"
                        }`}>
                        <input type="radio" name="pipeline_dag" value={d.id} checked={selectedDag === d.id}
                          onChange={() => setSelectedDag(d.id)}
                          className="w-4 h-4 accent-violet-600 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className={`font-bold text-[14px] ${selectedDag === d.id ? "text-violet-600" : "text-slate-800"}`}>{d.label}</div>
                          <div className="text-xs font-mono text-slate-400 mt-0.5">{d.id}</div>
                        </div>
                        <span className="text-slate-500 text-xs shrink-0 hidden sm:block mr-2">{d.desc}</span>
                        {/* Toggle switch for schedule */}
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[11px] text-slate-400 hidden sm:inline">{isPaused ? "Tắt" : "Bật"}</span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              void handleToggleSchedule(d.id, isPaused);
                            }}
                            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${!isPaused ? "bg-violet-600" : "bg-slate-200"}`}
                          >
                            <span
                              className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${!isPaused ? "translate-x-4" : "translate-x-0"}`}
                            />
                          </button>
                        </div>
                      </label>
                    );
                  })}
                </div>
                <div className="flex flex-col gap-2.5">
                  <button
                    disabled={triggerStatus === "loading"}
                    onClick={doTrigger}
                    className="bg-violet-600 hover:bg-violet-700 text-white font-semibold rounded-[10px] w-full p-3 flex items-center justify-center gap-2 text-[13.5px] transition disabled:opacity-70 disabled:cursor-not-allowed"
                  >
                    {triggerStatus === "loading"
                      ? <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Đang trigger...</>
                      : <><Icon name="play" size={16} />Trigger DAG</>}
                  </button>
                  {triggerStatus === "success" && (
                    <div className="p-2.5 px-3.5 rounded-[10px] bg-emerald-50 text-emerald-600 font-semibold text-[13px] flex items-center gap-2">
                      <Icon name="check" size={16} /> Run đã được tạo!
                    </div>
                  )}
                  {triggerStatus === "error" && (
                    <div className="p-2.5 px-3.5 rounded-[10px] bg-rose-50 text-rose-600 font-semibold text-[13px] flex items-center gap-2">
                      <Icon name="close" size={16} /> Lỗi kết nối Airflow!
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {/* Current DAG Progress */}
            <Card className="p-[22px] shadow-sm border-slate-200 rounded-[14px]">
              <div className="mb-[18px]">
                <h3 className="m-0 text-base font-bold mb-1">Tiến trình DAG hiện tại</h3>
                <p className="text-slate-500 m-0 text-[12.5px]">Trạng thái các task của {selectedInfo?.label || selectedDag}.</p>
              </div>
              <div className="flex flex-col gap-2">
                {(() => {
                  const run = data.recent_dag_runs.find(r => r.dag_id === selectedDag);
                  if (!run || !run.tasks || run.tasks.length === 0) {
                    return <div className="text-slate-400 text-[13px] text-center p-6 bg-slate-50 rounded-xl">Chưa có task nào chạy gần đây.</div>;
                  }
                  return run.tasks.map((t, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 px-4 rounded-[10px] bg-slate-50 border border-slate-100">
                      <span className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-white ${t.state === "success" ? "bg-emerald-500" : t.state === "running" ? "bg-violet-600" : t.state === "failed" ? "bg-rose-500" : "bg-slate-400"
                        }`}>
                        {t.state === "success" ? <Icon name="check" size={14} /> :
                          t.state === "running" ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> :
                            t.state === "failed" ? <Icon name="close" size={14} /> : <Icon name="clock" size={14} />}
                      </span>
                      <span className="flex-1 font-semibold text-[13.5px] font-mono text-slate-700 truncate">{t.task_id}</span>
                      <span className="text-slate-400 font-mono text-xs mr-2">{formatDuration(t.duration)}</span>
                      <div className="flex items-center gap-2">
                        {stateChip(t.state)}
                        {(t.state === "running" || t.state === "queued") && (
                          <button
                            type="button"
                            onClick={() => void handleCancelTask(t.task_id)}
                            className="px-2.5 py-1 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-[6px] transition shrink-0"
                            title="Hủy task (đánh dấu thất bại)"
                          >
                            Hủy
                          </button>
                        )}
                      </div>
                    </div>
                  ));
                })()}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
