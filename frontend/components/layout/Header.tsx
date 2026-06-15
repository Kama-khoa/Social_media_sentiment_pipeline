"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import { Icon } from "@/components/shared/Icon";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";

interface HeaderProps {
  title: string;
  onMenu: () => void;
}

const iconButtonClass = "grid h-9 w-9 place-items-center rounded-[10px] border-0 bg-transparent text-[var(--text-2)] transition-all hover:bg-[var(--surface-3)] hover:text-[var(--text)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[var(--ring)]";

export function Header({ title, onMenu }: HeaderProps) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const router = useRouter();
  const [quotaPct, setQuotaPct] = useState<number | null>(null);
  const [systemHealthy, setSystemHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    api.dashboard.admin().then(({ pipeline_status }) => {
      setQuotaPct(pipeline_status.quota_limit > 0 ? pipeline_status.quota_used_today / pipeline_status.quota_limit * 100 : 0);
      setSystemHealthy(pipeline_status.airflow_webserver === "healthy" && pipeline_status.airflow_scheduler === "healthy");
    }).catch(() => {
      setQuotaPct(null);
      setSystemHealthy(null);
    });
  }, []);

  function handleLogout() { logout(); router.push("/login"); }

  return <header className="sticky top-0 z-40 flex h-16 items-center gap-3.5 border-b border-[var(--border)] bg-[var(--nav-bg)] px-6 backdrop-blur-xl">
    <button className={`${iconButtonClass} admin-menu-btn hidden`} onClick={onMenu} aria-label="Mở menu"><Icon name="menu" size={20} /></button>
    <div className="min-w-0 flex-1">
      <h1 className="truncate text-[19px] font-extrabold tracking-normal">{title}</h1>
    </div>
    <div className="sys-status hidden items-center gap-3.5 md:flex">
      <span className="flex items-center gap-2 text-[12.5px] font-semibold text-[var(--text-2)]">
        <span className={`h-2 w-2 rounded-full ${systemHealthy === true ? "bg-[var(--pos)] [animation:pulseDot_1.4s_infinite]" : systemHealthy === false ? "bg-[var(--neg)]" : "bg-[var(--neu)]"}`} />
        {systemHealthy === true ? "Hệ thống hoạt động" : systemHealthy === false ? "Hệ thống cần kiểm tra" : "Đang kiểm tra hệ thống"}
      </span>
      {quotaPct !== null && <span className="chip num">Quota {quotaPct.toFixed(0)}%</span>}
    </div>
    <button className={iconButtonClass} onClick={toggleTheme} title="Sáng/tối" aria-label="Đổi giao diện sáng tối"><Icon name={theme === "dark" ? "sun" : "moon"} size={18} /></button>
    <Link href="/" className="hidden sm:block"><Button variant="outline" size="sm" className="h-9 rounded-[10px] px-3.5"><Icon name="external" size={16} />Trang công khai</Button></Link>
    <div className="flex items-center gap-2.5 border-l border-[var(--border)] pl-2">
      <span className="grid h-[34px] w-[34px] place-items-center rounded-full bg-gradient-to-br from-[var(--v-400)] to-[var(--v-600)] font-bold text-white">{user?.display_name?.charAt(0).toUpperCase() ?? "A"}</span>
      <div className="user-meta hidden leading-tight min-[720px]:block">
        <div className="text-[13.5px] font-bold">{user?.display_name}</div>
        <span className="chip brand mt-0.5 px-2 py-0 text-[10.5px]">Quản trị viên</span>
      </div>
      <button className={`${iconButtonClass} text-[var(--neg)] hover:text-[var(--neg)]`} onClick={handleLogout} title="Đăng xuất" aria-label="Đăng xuất"><Icon name="logout" size={18} /></button>
    </div>
  </header>;
}
