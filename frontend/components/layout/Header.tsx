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
    <Button variant="outline" size="icon" onClick={onMenu} className="lg:hidden"><Icon name="menu" size={20} /></Button>
    <h1 className="flex-1 text-[19px] font-extrabold tracking-[-.01em]">{title}</h1>
    <div className="hidden items-center gap-3.5 md:flex"><span className="flex items-center gap-2 text-[12.5px] font-semibold text-[var(--text-2)]"><span className={`h-2 w-2 rounded-full ${systemHealthy === true ? "bg-[var(--pos)] [animation:pulseDot_1.4s_infinite]" : systemHealthy === false ? "bg-[var(--neg)]" : "bg-[var(--neu)]"}`} />{systemHealthy === true ? "Hệ thống hoạt động" : systemHealthy === false ? "Hệ thống cần kiểm tra" : "Đang kiểm tra hệ thống"}</span>{quotaPct !== null && <span className="chip num">Quota {quotaPct.toFixed(0)}%</span>}</div>
    <Button variant="outline" size="icon" onClick={toggleTheme}><Icon name={theme === "dark" ? "sun" : "moon"} size={18} /></Button>
    <Link href="/" className="hidden sm:block"><Button variant="outline" size="sm"><Icon name="external" size={16} />Trang công khai</Button></Link>
    <div className="flex items-center gap-2.5 border-l border-[var(--border)] pl-2"><span className="grid h-[34px] w-[34px] place-items-center rounded-full bg-gradient-to-br from-[var(--v-400)] to-[var(--v-600)] font-bold text-white">{user?.display_name.charAt(0).toUpperCase()}</span><div className="hidden leading-tight xl:block"><div className="text-[13.5px] font-bold">{user?.display_name}</div><span className="chip brand mt-0.5 px-2 py-0 text-[10.5px]">Quản trị viên</span></div><Button variant="ghost" size="icon" onClick={handleLogout} className="text-[var(--neg)]"><Icon name="logout" size={18} /></Button></div>
  </header>;
}
