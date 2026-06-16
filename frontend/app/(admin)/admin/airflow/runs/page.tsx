"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api-client";
import type { PipelineHealthData } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";

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

export default function DagRunsPage() {
  const [data, setData] = useState<PipelineHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal log
  const [logModal, setLogModal] = useState<{dagId: string, runId: string, taskId: string, tryNumber: number} | null>(null);
  const [logContent, setLogContent] = useState<string | null>(null);
  const [loadingLog, setLoadingLog] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!logModal) return;
    let isMounted = true;
    
    async function pollLog() {
      try {
        const resp = await api.admin.pipeline.taskLog(logModal.dagId, logModal.runId, logModal.taskId, logModal.tryNumber);
        if (isMounted) {
          setLogContent(resp.content);
        }
      } catch {
        // Ignore polling errors
      }
    }

    const interval = setInterval(pollLog, 3000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [logModal]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logContent]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const h = await api.admin.pipeline.health();
      setData(h);
    } catch (err: unknown) {
      const e = err as { status?: number; detail?: string };
      setError(e?.detail || "Không thể tải dữ liệu lịch sử. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function openLog(dagId: string, runId: string, taskId: string, tryNumber: number) {
    setLogModal({ dagId, runId, taskId, tryNumber });
    setLogContent(null);
    setLoadingLog(true);
    try {
      const resp = await api.admin.pipeline.taskLog(dagId, runId, taskId, tryNumber);
      setLogContent(resp.content);
    } catch {
      setLogContent("Không thể tải nội dung log.");
    } finally {
      setLoadingLog(false);
    }
  }

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
        title="Lịch sử DAG Runs"
        description="Lịch sử các lần chạy pipeline điều phối bởi Airflow."
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
          <div className="grid grid-cols-2 md:grid-cols-4 gap-[14px] mb-[4px]">
            {[
              ["Thành công", data.recent_dag_runs.filter(r => r.state === "success").length, "text-emerald-500"], 
              ["Đang chạy", data.recent_dag_runs.filter(r => r.state === "running").length, "text-violet-600"], 
              ["Đang chờ", data.recent_dag_runs.filter(r => r.state === "queued").length, "text-slate-500"], 
              ["Thất bại", data.recent_dag_runs.filter(r => r.state === "failed").length, "text-rose-500"]
            ].map(([l, v, c]) => (
              <Card key={l as string} className="p-4 text-center">
                <div className={`text-[26px] font-bold ${c}`}>{v}</div>
                <div className="text-slate-500 text-[13px] font-semibold">{l}</div>
              </Card>
            ))}
          </div>
          <Card className="overflow-hidden shadow-sm border-slate-200 rounded-[14px]">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">DAG</th>
                    <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Run ID</th>
                    <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Bắt đầu</th>
                    <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Thời lượng</th>
                    <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Trạng thái</th>
                    <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Log</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_dag_runs.map((r, i) => (
                    <tr key={i} className="border-b border-slate-100 hover:bg-slate-50/50 last:border-0">
                      <td className="p-3.5 px-4 font-bold font-mono text-[13px] text-slate-700">{r.dag_id}</td>
                      <td className="p-3.5 px-4 text-slate-400 font-mono text-[12px] break-all max-w-[200px]">{r.run_id}</td>
                      <td className="p-3.5 px-4 text-slate-500 text-[13px]">{r.start_date ? new Date(r.start_date).toLocaleString("vi-VN") : "—"}</td>
                      <td className="p-3.5 px-4 text-slate-500 font-mono text-[13px]">{formatDuration(r.duration_seconds)}</td>
                      <td className="p-3.5 px-4">{stateChip(r.state)}</td>
                      <td className="p-3.5 px-4">
                        <button 
                          onClick={() => {
                            if (r.tasks && r.tasks.length > 0) {
                              openLog(r.dag_id, r.run_id, r.tasks[r.tasks.length-1].task_id, r.tasks[r.tasks.length-1].try_number);
                            } else {
                              alert("Không có task nào để xem log");
                            }
                          }}
                          className="w-8 h-8 rounded-lg border border-slate-200 bg-white flex items-center justify-center text-slate-500 hover:bg-slate-50 transition" title="Xem log task cuối">
                          <Icon name="external" size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                  {data.recent_dag_runs.length === 0 && (
                    <tr><td colSpan={6} className="p-8 text-center text-slate-400 text-sm">Chưa có dữ liệu</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* Log Modal */}
      {logModal && (
        <div className="fixed inset-0 bg-slate-900/60 z-50 flex items-center justify-center p-4" onClick={(e) => e.target === e.currentTarget && setLogModal(null)}>
          <Card className="w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl rounded-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-4 px-5 border-b border-slate-200 bg-slate-50">
              <div>
                <h3 className="font-bold text-base m-0">Airflow Task Log</h3>
                <div className="text-slate-500 text-[12px] font-mono mt-0.5">{logModal.dagId} / {logModal.taskId} (try {logModal.tryNumber})</div>
              </div>
              <button onClick={() => setLogModal(null)} className="w-8 h-8 rounded-full bg-slate-200/50 hover:bg-slate-200 flex items-center justify-center text-slate-600 transition">
                <Icon name="close" size={18} />
              </button>
            </div>
            <div ref={logContainerRef} className="flex-1 overflow-auto bg-slate-950 p-4 scroll-smooth">
              {loadingLog ? (
                <div className="h-full flex items-center justify-center text-slate-400">
                  <span className="w-6 h-6 border-2 border-slate-600 border-t-slate-400 rounded-full animate-spin mr-2" /> Đang tải log...
                </div>
              ) : (
                <pre className="text-[12px] font-mono text-slate-300 whitespace-pre-wrap break-all leading-5">
                  {logContent || "Không có nội dung log."}
                </pre>
              )}
            </div>
            <div className="p-3 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button onClick={() => setLogModal(null)} className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-[13px] font-semibold rounded-lg transition">
                Đóng
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
