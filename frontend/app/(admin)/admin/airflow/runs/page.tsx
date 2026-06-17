"use client";

import { useEffect, useState, useRef, useMemo, useCallback } from "react";
import { api } from "@/lib/api-client";
import type { DagRunDetail, TaskInstanceDetail } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/PageHeader";
import { Icon } from "@/components/shared/Icon";
import { Button } from "@/components/ui/button";
import { Dropdown } from "@/components/ui/dropdown";

const PAGE_SIZE = 10;

const DAG_OPTIONS = [
  { value: "", label: "Tất cả DAG" },
  { value: "youtube_daily_extraction_dag", label: "Thu thập YouTube" },
  { value: "sentiment_analysis_dag", label: "Phân tích cảm xúc NLP" },
  { value: "analytics_dag", label: "Tính toán Analytics" },
  { value: "seed_sync_dag", label: "Đồng bộ hạt giống" }
];

const STATUS_OPTIONS = [
  { value: "", label: "Tất cả trạng thái" },
  { value: "success", label: "Thành công" },
  { value: "failed", label: "Thất bại" },
  { value: "running", label: "Đang chạy" },
  { value: "queued", label: "Đang chờ" }
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

export default function DagRunsPage() {
  const [runs, setRuns] = useState<DagRunDetail[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Live timer for running durations
  const [now, setNow] = useState<Date>(new Date());

  // Filters
  const [dagFilter, setDagFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Cache bounds
  const [cachedStartPage, setCachedStartPage] = useState(1);
  const [cachedEndPage, setCachedEndPage] = useState(1);

  // Log pre-fetching caches
  const [taskCache, setTaskCache] = useState<Record<string, TaskInstanceDetail[]>>({});
  const [logCache, setLogCache] = useState<Record<string, { content: string; taskId: string; tryNumber: number }>>({});
  const [prefetchingRuns, setPrefetchingRuns] = useState<Record<string, boolean>>({});

  // Modal log states
  const [logModal, setLogModal] = useState<{ dagId: string; runId: string } | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeTryNumber, setActiveTryNumber] = useState<number>(1);
  const [logContent, setLogContent] = useState<string | null>(null);
  const [loadingLog, setLoadingLog] = useState(false);
  const [isModalLogFullScreen, setIsModalLogFullScreen] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const pageStart = (page - 1) * PAGE_SIZE;

  // The slice of runs visible on the current page
  const visibleRuns = useMemo(() => {
    const startIdx = (page - cachedStartPage) * PAGE_SIZE;
    if (startIdx < 0 || startIdx >= runs.length) {
      return [];
    }
    return runs.slice(startIdx, startIdx + PAGE_SIZE);
  }, [page, cachedStartPage, runs]);

  // Dynamic ticking timer for running DAG runs
  useEffect(() => {
    const hasRunning = runs.some(r => r.state === "running");
    if (!hasRunning) return;

    const timer = setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, [runs]);

  // Compute duration for running DAGs based on current time
  const getRunningDuration = useCallback((run: DagRunDetail) => {
    if (run.state === "running" && run.start_date) {
      try {
        const start = new Date(run.start_date);
        const diffMs = now.getTime() - start.getTime();
        return Math.max(0, Math.floor(diffMs / 1000));
      } catch {
        return run.duration_seconds;
      }
    }
    return run.duration_seconds;
  }, [now]);

  // Status counts based on the current cache of runs
  const counts = useMemo(() => {
    const c = { success: 0, running: 0, queued: 0, failed: 0 };
    runs.forEach(r => {
      const s = r.state?.toLowerCase();
      if (s === "success") c.success++;
      else if (s === "running") c.running++;
      else if (s === "queued" || s === "none") c.queued++;
      else if (s === "failed") c.failed++;
    });
    return c;
  }, [runs]);

  // Load runs with limit=30 and offset calculation
  const loadRuns = useCallback(async (targetPage: number, forceReload = false) => {
    setLoading(true);
    setError(null);
    try {
      // Check cache validity: we want targetPage to targetPage + 2 to be within [cachedStartPage, cachedEndPage]
      const isCached = !forceReload &&
        runs.length > 0 &&
        targetPage >= cachedStartPage &&
        (targetPage + 2 <= cachedEndPage || targetPage === totalPages || totalPages <= 3);

      if (!isCached) {
        const pagesToFetch = 3;
        const limit = PAGE_SIZE * pagesToFetch;
        const offset = (targetPage - 1) * PAGE_SIZE;

        const res = await api.admin.pipeline.allRuns({
          dagId: dagFilter || undefined,
          state: statusFilter || undefined,
          limit,
          offset,
        });

        setRuns(res.runs);
        setTotalCount(res.total_count);
        setCachedStartPage(targetPage);
        setCachedEndPage(targetPage + pagesToFetch - 1);
      }
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setError(e?.detail || "Không thể tải lịch sử DAG. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }, [dagFilter, statusFilter, cachedStartPage, cachedEndPage, runs.length, totalPages]);

  // Load runs on filters change or initial mount
  useEffect(() => {
    setPage(1);
    void loadRuns(1, true);
  }, [dagFilter, statusFilter]);

  // Load runs when page changes
  useEffect(() => {
    void loadRuns(page);
  }, [page]);

  // Background task lists and log pre-fetching for visible runs on the current page
  useEffect(() => {
    if (visibleRuns.length === 0) return;

    visibleRuns.forEach(async (run) => {
      const cacheKey = `${run.dag_id}_${run.run_id}`;
      
      if (!taskCache[cacheKey] && !prefetchingRuns[cacheKey]) {
        setPrefetchingRuns(prev => ({ ...prev, [cacheKey]: true }));
        try {
          const tasks = await api.admin.pipeline.tasks(run.dag_id, run.run_id);
          setTaskCache(prev => ({ ...prev, [cacheKey]: tasks }));

          const failedTask = tasks.find(t => t.state === "failed");
          const runningTask = tasks.find(t => t.state === "running");
          const targetTask = runningTask || failedTask || tasks[tasks.length - 1];

          if (targetTask) {
            const logContentResp = await api.admin.pipeline.taskLog(
              run.dag_id,
              run.run_id,
              targetTask.task_id,
              targetTask.try_number
            );
            
            setLogCache(prev => ({
              ...prev,
              [cacheKey]: {
                content: logContentResp.content,
                taskId: targetTask.task_id,
                tryNumber: targetTask.try_number
              }
            }));
          }
        } catch (err) {
          console.warn("Failed to prefetch tasks/logs for", cacheKey, err);
        } finally {
          setPrefetchingRuns(prev => ({ ...prev, [cacheKey]: false }));
        }
      }
    });
  }, [visibleRuns, taskCache, prefetchingRuns]);

  // Polling for logs when DAG run or active task is running (Real-time updates)
  useEffect(() => {
    if (!logModal) return;
    const cacheKey = `${logModal.dagId}_${logModal.runId}`;
    const run = runs.find(r => r.run_id === logModal.runId);
    
    const tasks = taskCache[cacheKey] || [];
    const activeTask = tasks.find(t => t.task_id === activeTaskId);
    const shouldPoll = (run?.state === "running") || (activeTask?.state === "running");
    
    if (!shouldPoll) return;

    let isMounted = true;
    
    const pollInterval = setInterval(async () => {
      try {
        // 1. Refresh tasks list
        const updatedTasks = await api.admin.pipeline.tasks(logModal.dagId, logModal.runId);
        if (isMounted) {
          setTaskCache(prev => ({ ...prev, [cacheKey]: updatedTasks }));
          
          // Auto-jump/focus if a different task starts running
          const runningTask = updatedTasks.find(t => t.state === "running");
          if (runningTask && runningTask.task_id !== activeTaskId) {
            setActiveTaskId(runningTask.task_id);
            setActiveTryNumber(runningTask.try_number);
          }
        }

        // 2. Fetch updated log content for the currently active task
        if (activeTaskId) {
          const currentActiveTask = updatedTasks.find(t => t.task_id === activeTaskId) || activeTask;
          const tryNum = currentActiveTask?.try_number || activeTryNumber;
          const resp = await api.admin.pipeline.taskLog(logModal.dagId, logModal.runId, activeTaskId, tryNum);
          if (isMounted) {
            setLogContent(resp.content);
          }
        }
      } catch (err) {
        console.warn("Real-time log polling error:", err);
      }
    }, 3000);

    return () => {
      isMounted = false;
      clearInterval(pollInterval);
    };
  }, [logModal, activeTaskId, activeTryNumber, runs, taskCache]);

  // Handle viewing log
  const handleOpenLog = async (run: DagRunDetail) => {
    setLogModal({ dagId: run.dag_id, runId: run.run_id });
    setLogContent(null);
    setLoadingLog(true);
    setIsModalLogFullScreen(false);

    const cacheKey = `${run.dag_id}_${run.run_id}`;
    let tasks = taskCache[cacheKey];

    // Fetch tasks if not cached
    if (!tasks) {
      try {
        tasks = await api.admin.pipeline.tasks(run.dag_id, run.run_id);
        setTaskCache(prev => ({ ...prev, [cacheKey]: tasks }));
      } catch {
        setLogContent("Không thể tải danh sách tasks.");
        setLoadingLog(false);
        return;
      }
    }

    // Target task: auto focus running task, then failed task, then last task
    const runningTask = tasks.find(t => t.state === "running");
    const failedTask = tasks.find(t => t.state === "failed");
    const targetTask = runningTask || failedTask || tasks[tasks.length - 1];

    if (!targetTask) {
      setLogContent("Không tìm thấy task nào trong run này.");
      setLoadingLog(false);
      return;
    }

    setActiveTaskId(targetTask.task_id);
    setActiveTryNumber(targetTask.try_number);

    // If pre-fetched cache exists, render immediately
    const cached = logCache[cacheKey];
    if (cached && cached.taskId === targetTask.task_id && cached.tryNumber === targetTask.try_number) {
      setLogContent(cached.content);
      setLoadingLog(false);
    } else {
      try {
        const resp = await api.admin.pipeline.taskLog(run.dag_id, run.run_id, targetTask.task_id, targetTask.try_number);
        setLogContent(resp.content);
      } catch {
        setLogContent("Không thể tải nội dung log.");
      } finally {
        setLoadingLog(false);
      }
    }
  };

  // Switch task inside log modal
  const handleSwitchTask = async (taskId: string, tryNumber: number) => {
    if (!logModal) return;
    setActiveTaskId(taskId);
    setActiveTryNumber(tryNumber);
    setLogContent(null);
    setLoadingLog(true);

    try {
      const resp = await api.admin.pipeline.taskLog(logModal.dagId, logModal.runId, taskId, tryNumber);
      setLogContent(resp.content);
    } catch {
      setLogContent("Không thể tải nội dung log.");
    } finally {
      setLoadingLog(false);
    }
  };

  const copyLogToClipboard = () => {
    if (logContent) {
      navigator.clipboard.writeText(logContent);
      alert("Đã sao chép log task vào clipboard!");
    }
  };

  const downloadTaskLogFile = () => {
    if (logModal && activeTaskId && logContent) {
      const element = document.createElement("a");
      const file = new Blob([logContent], {type: "text/plain"});
      element.href = URL.createObjectURL(file);
      element.download = `${logModal.dagId}_${activeTaskId}_try${activeTryNumber}.log`;
      document.body.appendChild(element);
      element.click();
      element.remove();
    }
  };

  return (
    <div className="flex flex-col gap-5 relative">
      <PageHeader
        title="Lịch sử DAG Runs"
        description="Lịch sử chi tiết toàn bộ các lần chạy của các DAG điều phối bởi Airflow."
        action={
          <button onClick={() => void loadRuns(page, true)} className="text-[13.5px] font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg px-3 py-1.5 hover:bg-slate-50 transition flex items-center gap-2">
            <Icon name="refresh" size={16} /> Làm mới
          </button>
        }
      />

      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-[13.5px] rounded-xl p-4">
          <strong>Lỗi kết nối:</strong> {error}
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-[14px] mb-[4px]">
        {[
          ["Thành công", counts.success, "text-emerald-500"], 
          ["Đang chạy", counts.running, "text-violet-600"], 
          ["Đang chờ", counts.queued, "text-slate-500"], 
          ["Thất bại", counts.failed, "text-rose-500"]
        ].map(([l, v, c]) => (
          <Card key={l as string} className="p-4 text-center">
            <div className={`text-[26px] font-bold ${c}`}>{v}</div>
            <div className="text-slate-500 text-[13px] font-semibold">{l}</div>
          </Card>
        ))}
      </div>

      <Card className="overflow-hidden shadow-sm border-slate-200 rounded-[14px]">
        {/* Table header filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 bg-slate-50/50">
          <div>
            <h3 className="font-bold text-[14.5px] text-slate-800 m-0">Danh sách lượt chạy</h3>
            <p className="text-xs text-slate-400 m-0 mt-0.5">{PAGE_SIZE} bản ghi/trang · dữ liệu đồng bộ từ Airflow.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Dropdown value={dagFilter} onChange={(e) => setDagFilter(e.target.value)} options={DAG_OPTIONS} placeholder="Tất cả DAG" className="w-48 h-[38px] text-[13px]" />
            <Dropdown value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} options={STATUS_OPTIONS} placeholder="Tất cả trạng thái" className="w-44 h-[38px] text-[13px]" />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">DAG</th>
                <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Run ID</th>
                <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Bắt đầu</th>
                <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Thời lượng</th>
                <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Trạng thái</th>
                <th className="p-3.5 px-4 font-semibold text-[13px] text-slate-500">Hành động</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: PAGE_SIZE }).map((_, row) => (
                  <tr key={row} className="border-b border-slate-100">
                    {Array.from({ length: 6 }).map((__, cell) => (
                      <td key={cell} className="p-3.5 px-4">
                        <div className="h-4 animate-pulse rounded bg-slate-100" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : visibleRuns.length > 0 ? (
                visibleRuns.map((r, i) => (
                  <tr key={i} className="border-b border-slate-100 hover:bg-slate-50/50 last:border-0">
                    <td className="p-3.5 px-4 font-bold font-mono text-[13px] text-slate-700">{r.dag_id}</td>
                    <td className="p-3.5 px-4 text-slate-400 font-mono text-[12px] break-all max-w-[240px]">{r.run_id}</td>
                    <td className="p-3.5 px-4 text-slate-500 text-[13px]">{r.start_date ? new Date(r.start_date).toLocaleString("vi-VN") : "—"}</td>
                    <td className="p-3.5 px-4 text-slate-500 font-mono text-[13px]">
                      {r.state === "running" ? (
                        <span className="text-violet-600 font-bold flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-violet-600 animate-ping" />
                          {formatDuration(getRunningDuration(r))}
                        </span>
                      ) : (
                        formatDuration(r.duration_seconds)
                      )}
                    </td>
                    <td className="p-3.5 px-4">{stateChip(r.state)}</td>
                    <td className="p-3.5 px-4">
                      <button 
                        onClick={() => void handleOpenLog(r)}
                        className="w-8 h-8 rounded-lg border border-slate-200 bg-white flex items-center justify-center text-slate-500 hover:bg-slate-50 transition hover:text-violet-600 hover:border-violet-200" 
                        title="Xem log chi tiết"
                      >
                        <Icon name="external" size={15} />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 text-sm">
                    Không tìm thấy lượt chạy phù hợp.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Section */}
        {!loading && totalCount > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-xs text-slate-500">
            <span>
              {totalCount} bản ghi tổng cộng · Hiển thị {pageStart + 1}-{Math.min(pageStart + PAGE_SIZE, totalCount)}
            </span>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                disabled={page <= 1} 
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                Trước
              </Button>
              <span className="text-slate-700 font-medium font-mono">Trang {page}/{totalPages}</span>
              <Button 
                variant="outline" 
                size="sm" 
                disabled={page >= totalPages} 
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              >
                Sau
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Log Modal with Split View: Task Timeline on the Left, Log content on the Right */}
      {logModal && (
        <div className="fixed inset-0 bg-slate-900/60 z-50 flex items-center justify-center p-4" onClick={(e) => e.target === e.currentTarget && setLogModal(null)}>
          <Card className="w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl rounded-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between p-4 px-5 border-b border-slate-200 bg-slate-50">
              <div>
                <h3 className="font-bold text-base m-0 text-slate-800">Lịch sử và Nhật ký tiến trình</h3>
                <div className="text-slate-500 text-[12px] font-mono mt-0.5">{logModal.dagId} / {logModal.runId}</div>
              </div>
              <button onClick={() => setLogModal(null)} className="w-8 h-8 rounded-full bg-slate-200/50 hover:bg-slate-200 flex items-center justify-center text-slate-600 transition">
                <Icon name="close" size={18} />
              </button>
            </div>
            
            <div className="flex-1 grid grid-cols-1 md:grid-cols-[280px_1fr] min-h-[500px] max-h-[70vh] overflow-hidden">
              {/* Left Panel: Task timeline */}
              <div className="border-r border-slate-200 bg-slate-50/50 overflow-y-auto p-4 flex flex-col gap-2">
                <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Các task thực thi</div>
                {(() => {
                  const cacheKey = `${logModal.dagId}_${logModal.runId}`;
                  const tasks = taskCache[cacheKey] || [];
                  if (tasks.length === 0) {
                    return (
                      <div className="flex items-center justify-center h-20 text-slate-400 text-xs">
                        Đang tải danh sách tasks...
                      </div>
                    );
                  }
                  return tasks.map((t, idx) => {
                    const isSelected = activeTaskId === t.task_id;
                    return (
                      <button
                        key={idx}
                        onClick={() => void handleSwitchTask(t.task_id, t.try_number)}
                        className={`w-full flex flex-col gap-1.5 p-3 rounded-xl border text-left transition-all ${
                          isSelected 
                            ? "bg-violet-50 border-violet-500 text-violet-900 shadow-sm" 
                            : "bg-white border-slate-200 hover:bg-slate-50 text-slate-700"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs font-bold truncate max-w-[150px]">{t.task_id}</span>
                          <span className={`w-2 h-2 rounded-full ${
                            t.state === "success" ? "bg-emerald-500" :
                            t.state === "running" ? "bg-violet-500 animate-pulse" :
                            t.state === "failed" ? "bg-rose-500" : "bg-slate-400"
                          }`} />
                        </div>
                        <div className="flex justify-between items-center text-[11px] text-slate-400">
                          <span>try {t.try_number}</span>
                          <span>{formatDuration(t.duration)}</span>
                        </div>
                      </button>
                    );
                  });
                })()}
              </div>

              {/* Right Panel: Log display */}
              <div className="flex flex-col bg-slate-950 overflow-hidden relative">
                <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between text-xs text-slate-400">
                  <span className="font-mono">
                    {activeTaskId ? `${activeTaskId} (try ${activeTryNumber})` : "Nhật ký"}
                  </span>
                  <div className="flex items-center gap-2">
                    {logContent && (
                      <>
                        <button onClick={downloadTaskLogFile} className="px-2.5 py-1 text-[11px] font-semibold border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded transition" title="Tải xuống log task này">
                          Tải log
                        </button>
                        <button onClick={copyLogToClipboard} className="px-2.5 py-1 text-[11px] font-semibold border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded transition" title="Sao chép log task này">
                          Sao chép
                        </button>
                        <button onClick={() => setIsModalLogFullScreen(true)} className="px-2.5 py-1 text-[11px] font-semibold border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded transition" title="Xem log toàn màn hình">
                          Toàn màn hình
                        </button>
                      </>
                    )}
                  </div>
                </div>

                <div ref={logContainerRef} className="flex-1 overflow-auto p-4 scroll-smooth">
                  {loadingLog ? (
                    <div className="h-full flex items-center justify-center text-slate-400">
                      <span className="w-6 h-6 border-2 border-slate-600 border-t-slate-400 rounded-full animate-spin mr-2" /> 
                      Đang tải log...
                    </div>
                  ) : (
                    <pre className="text-[12px] font-mono text-slate-300 whitespace-pre-wrap break-all leading-5">
                      {logContent || "Không có nội dung log."}
                    </pre>
                  )}
                </div>
              </div>
            </div>

            <div className="p-3 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button onClick={() => setLogModal(null)} className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-[13px] font-semibold rounded-lg transition">
                Đóng
              </button>
            </div>
          </Card>
        </div>
      )}

      {/* Task Log Full Screen Overlay */}
      {isModalLogFullScreen && logModal && activeTaskId && (
        <div className="fixed inset-0 bg-slate-950 z-[60] flex flex-col p-4 animate-in fade-in duration-150">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3 text-slate-300">
            <div>
              <div className="font-mono text-xs font-semibold">{logModal.dagId} / {activeTaskId}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">run_id: {logModal.runId} (try {activeTryNumber})</div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <button onClick={downloadTaskLogFile} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-850 hover:bg-slate-800 border border-slate-700 text-white rounded-lg transition">
                Tải tệp log
              </button>
              <button onClick={copyLogToClipboard} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-slate-850 hover:bg-slate-800 border border-slate-700 text-white rounded-lg transition">
                Sao chép
              </button>
              <button onClick={() => setIsModalLogFullScreen(false)} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-lg transition">
                Thoát toàn màn hình
              </button>
            </div>
          </div>
          <pre className="flex-1 overflow-auto bg-slate-900 text-slate-100 p-4 rounded-xl text-xs leading-5 font-mono whitespace-pre-wrap break-all">
            {logContent || "Không có nội dung log."}
          </pre>
        </div>
      )}
    </div>
  );
}
