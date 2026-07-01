"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { api } from "@/lib/api-client";
import type { ChannelConfigItem } from "@/lib/types";
import { Modal } from "@/components/admin/Modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Switch } from "@/components/ui/switch";
import { Icon } from "@/components/shared/Icon";
import { ChannelSuggestionModal } from "@/components/admin/ChannelSuggestionModal";
import { HistoricalBackfillModal } from "@/components/admin/HistoricalBackfillModal";

type ChannelForm = {
    channel_name: string;
    channel_url: string;
    channel_handle: string;
    subscriber_count: string;
};

type CrawlForm = {
    lookback_days: string;
};

const LOOKBACK_PRESETS = [3, 7, 30, 90, 180];
const PAGE_SIZE = 10;

function HistoricalBadge({ scanned }: { scanned: boolean }) {
    return <Badge variant={scanned ? "brand" : "warning"}>{scanned ? "Đã scan" : "Chưa scan"}</Badge>;
}

function quotaLabel(remaining: number | null) {
    if (remaining === null) return "Quota sẽ được kiểm tra khi trigger.";
    if (remaining < 100) return "API quota không đủ, hệ thống sẽ crawl bằng yt-dlp.";
    if (remaining < 500) return `Còn ${remaining.toLocaleString("vi-VN")} units, gần hết quota.`;
    return `Còn ${remaining.toLocaleString("vi-VN")} units API search.`;
}

export default function ChannelsPage() {
    const [channels, setChannels] = useState<ChannelConfigItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [pageError, setPageError] = useState<string | null>(null);
    const [mode, setMode] = useState<"add" | "edit" | null>(null);
    const [editTarget, setEditTarget] = useState<ChannelConfigItem | null>(null);
    const [crawlTarget, setCrawlTarget] = useState<ChannelConfigItem | null>(null);
    const [page, setPage] = useState(1);
    const [togglingId, setTogglingId] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const [crawling, setCrawling] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);
    const [crawlError, setCrawlError] = useState<string | null>(null);
  const [crawlResult, setCrawlResult] = useState<string | null>(null);
  const [crawlProgress, setCrawlProgress] = useState<number | null>(null);
  const [quotaRemaining, setQuotaRemaining] = useState<number | null>(null);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [backfillOpen, setBackfillOpen] = useState(false);
  const [showManualFallback, setShowManualFallback] = useState(false);
  const [manualUrl, setManualUrl] = useState("");
  const [deferredInfo, setDeferredInfo] = useState<string | null>(null);
  const [manualName, setManualName] = useState("");
  const [manualSubs, setManualSubs] = useState("");

    const { register, handleSubmit, reset, formState: { errors } } = useForm<ChannelForm>({
        defaultValues: { channel_name: "", channel_url: "", channel_handle: "", subscriber_count: "" },
    });
    const {
        register: registerCrawl,
        handleSubmit: handleCrawlSubmit,
        reset: resetCrawl,
    } = useForm<CrawlForm>({ defaultValues: { lookback_days: "30" } });

    async function load() {
        setLoading(true);
        setPageError(null);
        try {
            const [channelRows, quotaData] = await Promise.all([
                api.admin.channels.list(),
                api.admin.channels.quota().catch(() => null),
            ]);
            setChannels(channelRows);
            setPage((current) => Math.min(current, Math.max(1, Math.ceil(channelRows.length / PAGE_SIZE))));
            if (quotaData && typeof quotaData.search_remaining === "number") {
                setQuotaRemaining(quotaData.search_remaining);
            }
        } catch (err: unknown) {
            setPageError("Không thể tải danh sách kênh. Vui lòng thử lại.");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { load(); }, []);

    function openAdd() {
        reset({ channel_name: "", channel_url: "", channel_handle: "", subscriber_count: "" });
        setEditTarget(null);
        setFormError(null);
        setMode("add");
    }

    function openEdit(ch: ChannelConfigItem) {
        reset({
            channel_name: ch.channel_name,
            channel_url: ch.channel_url ?? "",
            channel_handle: ch.channel_handle ?? "",
            subscriber_count: ch.subscriber_count?.toString() ?? "",
        });
        setEditTarget(ch);
        setFormError(null);
        setMode("edit");
    }

    function openCrawl(ch: ChannelConfigItem) {
        resetCrawl({ lookback_days: "30" });
        setCrawlTarget(ch);
        setCrawlError(null);
        setCrawlResult(null);
        setCrawlProgress(null);
    }

    async function onSubmit(data: ChannelForm) {
        setSaving(true);
        setFormError(null);
        setDeferredInfo(null);
        try {
            if (mode === "add") {
                const res = await api.admin.channels.create({ channel_url: data.channel_url.trim() });
                if (res.subscriber_count === -1) {
                    setDeferredInfo("Kênh đã được thêm thành công dưới dạng danh sách chờ. Thông tin kênh sẽ được tự động đồng bộ đầy đủ vào ngày mai.");
                }
            } else if (editTarget) {
                await api.admin.channels.update(editTarget.channel_id, {
                    channel_name: data.channel_name.trim(),
                    channel_url: data.channel_url.trim() || undefined,
                    channel_handle: data.channel_handle.trim() || undefined,
                    subscriber_count: data.subscriber_count ? parseInt(data.subscriber_count, 10) : undefined,
                });
            }
            setMode(null);
            await load();
        } catch (err: unknown) {
            const e = err as { status?: number; detail?: string };
            if (mode === "add" && e?.status === 429) {
                setManualUrl(data.channel_url.trim());
                setManualName("");
                setManualSubs("");
                setMode(null);
                setShowManualFallback(true);
            } else {
                setFormError(e?.detail ?? "Không thể lưu thay đổi.");
            }
        } finally {
            setSaving(false);
        }
    }

    async function onSubmitManual(isDeferred: boolean) {
        setSaving(true);
        setFormError(null);
        try {
            const payload: any = {
                channel_url: manualUrl,
                bypass_resolve: true,
            };
            if (isDeferred) {
                payload.subscriber_count = -1;
            } else {
                if (!manualName.trim()) {
                    setFormError("Vui lòng nhập tên kênh.");
                    setSaving(false);
                    return;
                }
                payload.channel_name = manualName.trim();
                payload.subscriber_count = manualSubs ? parseInt(manualSubs, 10) : 0;
            }

            const res = await api.admin.channels.create(payload);
            setShowManualFallback(false);
            if (res.subscriber_count === -1) {
                setDeferredInfo("Kênh đã được thêm thành công dưới dạng danh sách chờ. Thông tin kênh sẽ được tự động đồng bộ đầy đủ vào ngày mai.");
            } else {
                setDeferredInfo(null);
            }
            await load();
        } catch (err: unknown) {
            const e = err as { detail?: string };
            setFormError(e?.detail ?? "Không thể lưu thông tin kênh.");
        } finally {
            setSaving(false);
        }
    }

    async function onCrawl(data: CrawlForm) {
        if (!crawlTarget) return;
        setCrawling(true);
        setCrawlError(null);
        setCrawlResult(null);
        setCrawlProgress(0);

        let runIdToPoll: string | null = null;
        let dagIdToPoll: string | null = null;

        try {
            const lookback = parseInt(data.lookback_days, 10);
            const result = await api.admin.channels.crawl(crawlTarget.channel_id, {
                lookback_days: lookback,
                preferred_mode: "auto",
            });
            runIdToPoll = result.run_id ?? null;
            dagIdToPoll = result.dag_id ?? null;
            setQuotaRemaining(result.quota_remaining);
        } catch (err: unknown) {
            const e = err as { detail?: string };
            setCrawlError(e?.detail ?? "Không thể trigger crawl.");
            setCrawling(false);
            setCrawlProgress(null);
            return;
        }

        if (!runIdToPoll || !dagIdToPoll) {
            setCrawlError("Đã trigger crawl nhưng không lấy được ID tiến trình.");
            setCrawling(false);
            setCrawlProgress(null);
            return;
        }

        let progress = 0;
        while (progress < 100) {
            await new Promise((resolve) => setTimeout(resolve, 3000));

            try {
                const tiData: any = await api.admin.pipeline.tasks(dagIdToPoll, runIdToPoll);
                const tasks = tiData?.task_instances || [];

                const getTaskState = (id: string) => tasks.find((t: any) => t.task_id === id)?.state;
                const eltState = getTaskState("run_youtube_elt");
                const dbtState = getTaskState("prepare_downstream_models");

                console.log(`[DAG Polling] Run ID: ${runIdToPoll} | Tasks: ${tasks.length} | ELT: ${eltState || 'N/A'} | DBT: ${dbtState || 'N/A'}`);

                if (eltState === "failed" || dbtState === "failed" || eltState === "upstream_failed" || dbtState === "upstream_failed") {
                    setCrawlError("Thu thập dữ liệu thất bại. Task trong tiến trình đã bị lỗi.");
                    break;
                }

                let newProgress = 10;
                if (tasks.length === 0) {
                    newProgress = 5;
                } else if (eltState === "success") {
                    newProgress = 60;
                    if (dbtState === "success") {
                        newProgress = 100;
                    } else if (dbtState === "running") {
                        newProgress = 80;
                    }
                } else if (eltState === "running") {
                    newProgress = Math.min(50, progress + 5);
                }

                setCrawlProgress(newProgress);
                progress = newProgress;

                if (newProgress === 100) {
                    setCrawlResult("Đã hoàn thành thu thập dữ liệu kênh.");
                    break;
                }

                const runsData: any = await api.admin.pipeline.runs(dagIdToPoll, 5);
                const currentRun = runsData?.dag_runs?.find((r: any) => r.dag_run_id === runIdToPoll);
                if (currentRun) {
                    if (currentRun.state === "failed") {
                        setCrawlError("Tiến trình thu thập đã bị ngừng hoặc lỗi.");
                        break;
                    } else if (currentRun.state === "success") {
                        setCrawlProgress(100);
                        setCrawlResult("Đã hoàn thành thu thập dữ liệu kênh.");
                        break;
                    }
                }
            } catch (err) {
                // silent fail on polling error, continue trying
            }
        }
        setCrawling(false);
    }

    async function handleToggleActive(ch: ChannelConfigItem) {
        setTogglingId(ch.channel_id);
        setPageError(null);
        try {
            await api.admin.channels.update(ch.channel_id, { is_active: !ch.is_active });
            setChannels((prev) => prev.map((c) => c.channel_id === ch.channel_id ? { ...c, is_active: !ch.is_active } : c));
        } catch (err: unknown) {
            const e = err as { detail?: string };
            setPageError(e?.detail ?? "Không thể cập nhật trạng thái kênh. Vui lòng thử lại.");
        } finally {
            setTogglingId(null);
        }
    }

    const activeCount = channels.filter((c) => c.is_active).length;
    const totalPages = Math.max(1, Math.ceil(channels.length / PAGE_SIZE));
    const pageStart = (page - 1) * PAGE_SIZE;
    const pagedChannels = channels.slice(pageStart, pageStart + PAGE_SIZE);

    return (
        <div>
          <div className="mb-6">
        <PageHeader
          title="Quản lý kênh YouTube"
          description={quotaLabel(quotaRemaining)}
          action={
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setSuggestOpen(true)}>
                <Icon name="spark" size={16} className="mr-1.5 text-amber-500" />
                Gợi ý kênh
              </Button>
              <Button variant="outline" onClick={() => setBackfillOpen(true)}>
                <Icon name="clock" size={16} className="mr-1.5 text-indigo-500" />
                Quét lịch sử
              </Button>
              <Button onClick={openAdd}>
                <Icon name="plus" size={16} className="mr-1.5" />
                Thêm kênh
              </Button>
            </div>
          }
        />
      </div>

            {deferredInfo && (
                <div className="mb-4 bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Icon name="clock" size={16} className="text-amber-600 mr-1.5" />
                        <span>{deferredInfo}</span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setDeferredInfo(null)} className="h-auto p-1 text-amber-700 hover:bg-amber-100">Đóng</Button>
                </div>
            )}

            {pageError && (
                <div className="mb-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg px-4 py-3">
                    {pageError}
                </div>
            )}

            <Card className="overflow-hidden shadow-none">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-slate-200 bg-slate-50">
                            <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Kênh</th>
                            <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Handle</th>
                            <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Người đăng ký</th>
                            <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Trạng thái</th>
                            <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Historical</th>
                            <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium uppercase tracking-wider">Ngày thêm</th>
                            <th className="px-4 py-3 text-right text-xs text-slate-500 font-medium uppercase tracking-wider">Hành động</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            Array.from({ length: 5 }).map((_, i) => (
                                <tr key={i} className="border-b border-slate-100">
                                    {Array.from({ length: 7 }).map((_, j) => (
                                        <td key={j} className="px-4 py-4"><div className="h-4 bg-slate-100 rounded animate-pulse" /></td>
                                    ))}
                                </tr>
                            ))
                        ) : channels.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-4 py-12 text-center text-slate-400 text-sm">
                                    Chưa có kênh nào. Nhấn &ldquo;Thêm kênh&rdquo; để bắt đầu.
                                </td>
                            </tr>
                        ) : (
                            pagedChannels.map((ch) => (
                                <tr key={ch.channel_id} className={`border-b border-slate-100 hover:bg-slate-50/50 transition-colors ${!ch.is_active ? "opacity-60" : ""}`}>
                                    <td className="px-4 py-3.5">
                                        <div className="flex items-center gap-2.5">
                                            <span className="grid h-8 w-8 place-items-center rounded-[9px] bg-[var(--surface-3)] text-[var(--primary)]"><Icon name="broadcast" size={16} /></span>
                                            <div>
                                                <div className="font-medium text-slate-800">{ch.channel_name}</div>
                                                <div className="text-xs text-slate-400 font-mono mt-0.5">{ch.channel_id}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-4 py-3.5 text-slate-500 text-xs">{ch.channel_handle ?? "—"}</td>
                                    <td className="num px-4 py-3.5 text-xs">{ch.subscriber_count?.toLocaleString("vi-VN") ?? "—"}</td>
                                    <td className="px-4 py-3.5">
                                        <div className="flex items-center gap-2">
                                            <Switch
                                                checked={ch.is_active}
                                                onClick={() => handleToggleActive(ch)}
                                                disabled={togglingId === ch.channel_id}
                                                label={`${ch.is_active ? "Tắt" : "Bật"} ${ch.channel_name}`}
                                            />
                                            <StatusBadge active={ch.is_active} />
                                        </div>
                                    </td>
                                    <td className="px-4 py-3.5"><HistoricalBadge scanned={ch.is_historically_scanned} /></td>
                                    <td className="px-4 py-3.5 text-xs text-slate-400">{new Date(ch.created_at).toLocaleDateString("vi-VN")}</td>
                                    <td className="px-4 py-3.5">
                                        <div className="flex items-center justify-end gap-2">
                                            {ch.is_active && (
                                                <Button onClick={() => openCrawl(ch)} variant="outline" size="sm">
                                                    <Icon name="play" size={13} />Thu thập
                                                </Button>
                                            )}
                                            <Button onClick={() => openEdit(ch)} variant="ghost" size="sm" className="text-indigo-600 hover:text-indigo-800">Sửa</Button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>

                {!loading && channels.length > 0 && (
                    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-xs text-slate-400">
                        <span>
                            {activeCount} kênh đang hoạt động · {channels.length} tổng cộng · Hiển thị {pageStart + 1}-{Math.min(pageStart + PAGE_SIZE, channels.length)}
                        </span>
                        <div className="flex items-center gap-2">
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                disabled={page <= 1}
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                            >
                                Trước
                            </Button>
                            <span className="num text-slate-500">Trang {page}/{totalPages}</span>
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                disabled={page >= totalPages}
                                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            >
                                Sau
                            </Button>
                        </div>
                    </div>
                )}
            </Card>

            <Modal open={mode !== null} title={mode === "add" ? "Thêm kênh YouTube" : "Sửa thông tin kênh"} onClose={() => setMode(null)}>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                    {formError && <div className="bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg px-3 py-2">{formError}</div>}

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">URL kênh <span className="text-rose-500">*</span></label>
                        <Input
                            {...register("channel_url", { required: "Bắt buộc" })}
                            placeholder="https://www.youtube.com/@channelname"
                        />
                        {errors.channel_url && <p className="text-xs text-rose-500 mt-1">{errors.channel_url.message}</p>}
                    </div>

                    {mode === "edit" && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Tên kênh <span className="text-rose-500">*</span></label>
                                <Input {...register("channel_name", { required: "Bắt buộc" })} placeholder="Tên hiển thị của kênh" />
                                {errors.channel_name && <p className="text-xs text-rose-500 mt-1">{errors.channel_name.message}</p>}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Handle</label>
                                <Input {...register("channel_handle")} placeholder="@channelname" />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Số người đăng ký</label>
                                <Input
                                    {...register("subscriber_count", {
                                        pattern: { value: /^\d*$/, message: "Phải là số nguyên dương" },
                                    })}
                                    placeholder="1000000"
                                />
                                {errors.subscriber_count && <p className="text-xs text-rose-500 mt-1">{errors.subscriber_count.message}</p>}
                            </div>
                        </>
                    )}

                    <div className="flex justify-end gap-3 pt-2">
                        <Button type="button" onClick={() => setMode(null)} variant="outline">Hủy</Button>
                        <Button type="submit" disabled={saving}>{saving ? "Đang lưu..." : mode === "add" ? "Thêm kênh" : "Lưu thay đổi"}</Button>
                    </div>
                </form>
            </Modal>

            <Modal open={crawlTarget !== null} title="Thu thập dữ liệu kênh" onClose={() => setCrawlTarget(null)}>
                <form onSubmit={handleCrawlSubmit(onCrawl)} className="space-y-5">
                    <div>
                        <p className="text-sm font-medium text-slate-800">{crawlTarget?.channel_name}</p>
                        <p className="text-xs text-slate-400 mt-1">{quotaLabel(quotaRemaining)}</p>
                    </div>

                    {crawlError && <div className="bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg px-3 py-2">{crawlError}</div>}
                    {crawlResult && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs rounded-lg px-3 py-2">{crawlResult}</div>}

                    {crawlProgress !== null && (
                        <div className="space-y-1.5 mt-2 mb-4">
                            <div className="flex justify-between text-xs font-medium text-slate-500">
                                <span>Tiến trình thu thập & transform</span>
                                <span>{crawlProgress}%</span>
                            </div>
                            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                                <div
                                    className={`h-2 rounded-full transition-all duration-500 ${crawlError ? 'bg-rose-500' : crawlProgress === 100 ? 'bg-emerald-500' : 'bg-indigo-500'}`}
                                    style={{ width: `${crawlProgress}%` }}
                                />
                            </div>
                        </div>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Khoảng thời gian</label>
                        <Select {...registerCrawl("lookback_days")} disabled={crawling}>
                            {LOOKBACK_PRESETS.map((days) => (
                                <option key={days} value={days}>{days} ngày gần nhất</option>
                            ))}
                        </Select>
                    </div>

          <div className="flex justify-end gap-3">
            <Button type="button" onClick={() => setCrawlTarget(null)} variant="outline" disabled={crawling}>Đóng</Button>
            <Button type="submit" disabled={crawling || crawlProgress === 100}>
              <Icon name="play" size={14} className="mr-1.5" />{crawling ? "Đang thu thập..." : crawlProgress === 100 ? "Hoàn tất" : quotaRemaining !== null && quotaRemaining < 100 ? "Crawl bằng yt-dlp" : "Thu thập dữ liệu"}
            </Button>
          </div>
        </form>
      </Modal>

      <ChannelSuggestionModal 
        open={suggestOpen} 
        onClose={() => setSuggestOpen(false)} 
        onAdded={() => { load(); }} 
      />
      
      <HistoricalBackfillModal 
        open={backfillOpen} 
        onClose={() => setBackfillOpen(false)} 
      />

      <Modal open={showManualFallback} title="Hết Quota - Nhập thông tin kênh thủ công" onClose={() => setShowManualFallback(false)}>
          <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-lg px-3 py-2">
                  Hệ thống đã hết quota YouTube API hôm nay và bị YouTube chặn cào tự động. Bạn có thể tự điền thông tin hoặc lưu tạm thời chờ đồng bộ tự động.
              </div>

              <div className="text-xs text-slate-500 break-all">
                  <strong>URL kênh:</strong> {manualUrl}
              </div>

              {formError && <div className="bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg px-3 py-2">{formError}</div>}

              <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Tên kênh</label>
                  <Input
                      value={manualName}
                      onChange={(e) => setManualName(e.target.value)}
                      placeholder="Ví dụ: Schannel"
                      disabled={saving}
                  />
              </div>

              <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Số lượng người đăng ký (sub)</label>
                  <Input
                      value={manualSubs}
                      onChange={(e) => setManualSubs(e.target.value)}
                      placeholder="Ví dụ: 1500000"
                      disabled={saving}
                  />
              </div>

              <div className="flex justify-between items-center pt-2 gap-3">
                  <Button type="button" onClick={() => onSubmitManual(true)} variant="outline" className="border-amber-300 text-amber-700 hover:bg-amber-50" disabled={saving}>
                      {saving ? "Đang xử lý..." : "Lưu tạm thời (Hàng chờ)"}
                  </Button>
                  <div className="flex gap-2">
                      <Button type="button" onClick={() => setShowManualFallback(false)} variant="outline" disabled={saving}>Hủy</Button>
                      <Button type="button" onClick={() => onSubmitManual(false)} disabled={saving}>Lưu thủ công</Button>
                  </div>
              </div>
          </div>
      </Modal>
    </div>
  );
}
