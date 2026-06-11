"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useTheme } from "@/lib/theme-context";
import { Icon, type IconName } from "@/components/shared/Icon";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface GuestHeaderProps {
  title: string;
}

const tabs: Array<{ href: string; label: string; icon: IconName }> = [
  { href: "/#search", label: "Tìm kiếm", icon: "search" },
  { href: "/", label: "Top sản phẩm", icon: "trophy" },
];

function navigatePublicTab(href: string) {
  const nextHash = href === "/#search" ? "#search" : "";
  window.history.pushState(null, "", href);
  window.dispatchEvent(new CustomEvent("techchoice:public-tab", { detail: nextHash }));
}

export function GuestHeader({ title }: GuestHeaderProps) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const pathname = usePathname();
  const router = useRouter();
  const [accountOpen, setAccountOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [hash, setHash] = useState("");
  const accountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function closeAccount(event: MouseEvent) {
      if (accountRef.current && !accountRef.current.contains(event.target as Node)) setAccountOpen(false);
    }
    document.addEventListener("mousedown", closeAccount);
    return () => document.removeEventListener("mousedown", closeAccount);
  }, []);

  useEffect(() => {
    function syncHash() { setHash(window.location.hash); }
    syncHash();
    window.addEventListener("hashchange", syncHash);
    window.addEventListener("popstate", syncHash);
    return () => {
      window.removeEventListener("hashchange", syncHash);
      window.removeEventListener("popstate", syncHash);
    };
  }, []);

  function handleLogout() {
    logout();
    setAccountOpen(false);
    router.push("/");
  }

  function handleTabClick(event: React.MouseEvent<HTMLAnchorElement>, href: string) {
    if (pathname !== "/") return;
    event.preventDefault();
    navigatePublicTab(href);
    setHash(href === "/#search" ? "#search" : "");
    setMobileOpen(false);
  }

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--nav-bg)] backdrop-blur-2xl">
      <div className="mx-auto flex h-16 max-w-[1240px] items-center gap-[18px] px-6">
        <Link href="/" className="focusable flex items-center gap-[11px] rounded-xl">
          <span className="grid h-[34px] w-[34px] place-items-center rounded-[10px] bg-gradient-to-br from-[var(--v-500)] to-[var(--v-700)] text-white shadow-[0_6px_14px_-4px_var(--ring)]"><Icon name="spark" size={19} /></span>
          <span className="text-[19px] font-extrabold tracking-[-.02em] text-[var(--text)]">{title.slice(0, 4)}<span className="text-[var(--primary)]">{title.slice(4)}</span></span>
        </Link>

        <nav className="hidden flex-1 justify-center gap-1.5 md:flex">
          {tabs.map((tab) => {
            const active = pathname === "/" && (tab.href === "/#search" ? hash === "#search" : hash !== "#search");
            return <Link key={tab.label} href={tab.href} onClick={(event) => handleTabClick(event, tab.href)} className={`focusable flex items-center gap-2 rounded-[11px] px-[18px] py-2.5 text-[14.5px] font-semibold transition-all ${active ? "bg-[var(--primary-soft)] text-[var(--primary)]" : "text-[var(--text-2)] hover:bg-[var(--surface-3)]"}`}><Icon name={tab.icon} size={17} />{tab.label}</Link>;
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2.5">
          <Button variant="outline" size="icon" onClick={toggleTheme} title="Đổi giao diện sáng/tối"><Icon name={theme === "dark" ? "sun" : "moon"} size={18} /></Button>
          {!user ? (
            <div className="hidden gap-2 md:flex">
              <Link href="/login"><Button variant="outline" size="sm">Đăng nhập</Button></Link>
              <Link href="/register"><Button size="sm">Đăng ký</Button></Link>
            </div>
          ) : (
            <div ref={accountRef} className="relative">
              <button onClick={() => setAccountOpen((open) => !open)} className="focusable flex items-center gap-2 rounded-full border border-[var(--border-strong)] bg-[var(--surface)] p-[5px] pr-[11px] text-[var(--text)]">
                <span className="grid h-[30px] w-[30px] place-items-center rounded-full bg-gradient-to-br from-[var(--v-400)] to-[var(--v-600)] text-[13px] font-bold text-white">{user.display_name.charAt(0).toUpperCase()}</span>
                <span className="hidden text-sm font-semibold sm:block">{user.display_name}</span>
                <Icon name="chevron" size={15} style={{ color: "var(--text-3)" }} />
              </button>
              {accountOpen && (
                <Card className="absolute right-0 top-[calc(100%+10px)] w-60 p-2 shadow-[var(--shadow-lg)] [animation:pop_.15s_ease_both]">
                  <div className="px-3 py-2.5"><div className="text-sm font-bold">{user.display_name}</div><div className="faint text-xs">{user.email}</div><span className="chip brand mt-2">{user.role === "admin" ? "Quản trị viên" : "Người dùng"}</span></div>
                  <hr className="divider" />
                  {user.role === "admin" && <DropItem href="/admin" icon="grid" label="Trang quản trị" highlight />}
                  <DropItem href="/favorites" icon="heart" label="Sản phẩm đã lưu" />
                  <hr className="divider" />
                  <DropItem icon="logout" label="Đăng xuất" danger onClick={handleLogout} />
                </Card>
              )}
            </div>
          )}
          <Button variant="outline" size="icon" onClick={() => setMobileOpen((open) => !open)} className="md:hidden"><Icon name={mobileOpen ? "close" : "menu"} size={20} /></Button>
        </div>
      </div>
      {mobileOpen && <div className="flex flex-col gap-1 border-t border-[var(--border)] bg-[var(--surface)] p-3 md:hidden">{tabs.map((tab) => <Link key={tab.label} href={tab.href} onClick={(event) => handleTabClick(event, tab.href)} className="flex items-center gap-2.5 rounded-[10px] px-3.5 py-3 text-[15px] font-semibold text-[var(--text)] hover:bg-[var(--primary-soft)] hover:text-[var(--primary)]"><Icon name={tab.icon} size={18} />{tab.label}</Link>)}{!user && <div className="mt-1.5 flex gap-2"><Link href="/login" className="flex-1"><Button variant="outline" className="w-full">Đăng nhập</Button></Link><Link href="/register" className="flex-1"><Button className="w-full">Đăng ký</Button></Link></div>}</div>}
    </header>
  );
}

function DropItem({ icon, label, href, danger, highlight, onClick }: { icon: IconName; label: string; href?: string; danger?: boolean; highlight?: boolean; onClick?: () => void }) {
  const className = `focusable flex w-full items-center gap-[11px] rounded-[9px] px-3 py-2.5 text-left text-sm font-semibold transition-colors hover:bg-[var(--surface-3)] ${danger ? "text-[var(--neg)]" : highlight ? "text-[var(--primary)]" : "text-[var(--text)]"}`;
  const content = <><Icon name={icon} size={17} />{label}</>;
  return href ? <Link href={href} className={className}>{content}</Link> : <button onClick={onClick} className={className}>{content}</button>;
}
