"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon, type IconName } from "@/components/shared/Icon";

interface AdminSidebarProps {
  open: boolean;
  onClose: () => void;
}

type AdminMenuItem = { href: string; label: string; icon: IconName; group: string };

const items: AdminMenuItem[] = [
  { href: "/admin", label: "Tổng quan phân tích", icon: "grid", group: "PHÂN TÍCH" },
  { href: "/admin/channels", label: "Quản lý kênh", icon: "broadcast", group: "THU THẬP" },
  { href: "/admin/keywords", label: "Quản lý từ khóa", icon: "tag", group: "THU THẬP" },
  { href: "/admin/products", label: "Quản lý sản phẩm", icon: "box", group: "SẢN PHẨM" },
  { href: "/admin/products/aliases", label: "Tên gọi khác", icon: "link", group: "SẢN PHẨM" },
  { href: "/admin/products/candidates", label: "Duyệt ánh xạ SP", icon: "inbox", group: "SẢN PHẨM" },
  { href: "/admin/products/spec-templates", label: "Mẫu thông số", icon: "spec", group: "SẢN PHẨM" },
  { href: "/admin/airflow", label: "Tình trạng Pipeline", icon: "heart", group: "HỆ THỐNG" },
  { href: "/admin/airflow#runs", label: "Lịch sử DAG Runs", icon: "flow", group: "HỆ THỐNG" },
  { href: "/admin/airflow#ops", label: "Chỉ số vận hành", icon: "activity", group: "HỆ THỐNG" },
  { href: "/admin/users", label: "Quản lý tài khoản", icon: "users", group: "HỆ THỐNG" },
  { href: "/admin/logs", label: "Log pipeline", icon: "server", group: "HỆ THỐNG" },
];

function splitHref(href: string) {
  const [path, hash] = href.split("#");
  return { path, hash: hash ? `#${hash}` : "" };
}

export function AdminSidebar({ open, onClose }: AdminSidebarProps) {
  const pathname = usePathname();
  const [hash, setHash] = useState("");
  const groups = useMemo(() => Array.from(new Set(items.map((item) => item.group))), []);

  useEffect(() => {
    const syncHash = () => setHash(window.location.hash);
    syncHash();
    window.addEventListener("hashchange", syncHash);
    window.addEventListener("popstate", syncHash);
    return () => {
      window.removeEventListener("hashchange", syncHash);
      window.removeEventListener("popstate", syncHash);
    };
  }, [pathname]);

  function isActive(href: string) {
    const { path, hash: itemHash } = splitHref(href);
    if (pathname !== path) return false;
    if (itemHash) return hash === itemHash;
    const activeSiblingHash = items.some((item) => {
      const sibling = splitHref(item.href);
      return sibling.path === path && sibling.hash && sibling.hash === hash;
    });
    return !activeSiblingHash;
  }

  return <>
    {open && <button className="admin-sidebar-scrim fixed inset-0 z-[60] hidden bg-[#140c2880]" onClick={onClose} aria-label="Đóng menu" />}
    <aside className={`admin-sidebar fixed inset-y-0 left-0 z-[70] flex w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] min-[941px]:sticky min-[941px]:top-0 min-[941px]:z-30 min-[941px]:h-screen min-[941px]:translate-x-0 ${open ? "open" : ""}`}>
      <Link href="/admin" className="flex items-center gap-[11px] px-5 pb-3.5 pt-5">
        <span className="grid h-[34px] w-[34px] place-items-center rounded-[10px] bg-gradient-to-br from-[var(--v-500)] to-[var(--v-700)] text-white"><Icon name="spark" size={19} /></span>
        <span><span className="block text-base font-extrabold tracking-normal">TechChoice</span><span className="faint block text-[11px] font-semibold tracking-[.04em]">BẢNG QUẢN TRỊ</span></span>
      </Link>
      <nav className="flex-1 overflow-y-auto px-3 py-1.5">
        {groups.map((group) => (
          <div key={group}>
            <div className="faint px-3 pb-[5px] pt-3.5 text-[10.5px] font-bold uppercase tracking-[.07em]">{group}</div>
            {items.filter((item) => item.group === group).map((item) => {
              const active = isActive(item.href);
              return <Link key={item.href} href={item.href} onClick={onClose} className={`relative mb-0.5 flex items-center gap-[11px] rounded-[10px] px-3 py-[9px] text-[13.5px] font-semibold transition-all ${active ? "bg-[var(--primary-soft)] text-[var(--primary)]" : "text-[var(--text-2)] hover:bg-[var(--surface-3)] hover:text-[var(--text)]"}`}>{active && <span className="absolute bottom-2 left-0 top-2 w-[3px] rounded-full bg-[var(--primary)]" />}<Icon name={item.icon} size={16} />{item.label}</Link>;
            })}
          </div>
        ))}
      </nav>
      <div className="border-t border-[var(--border)] p-3.5"><div className="card flex items-center gap-2.5 bg-[var(--surface-2)] p-3"><span className="h-2 w-2 rounded-full bg-[var(--pos)] [animation:pulseDot_1.4s_infinite]" /><div className="text-xs"><div className="font-bold">Hệ thống ổn định</div><div className="faint">Airflow · BigQuery · Redis</div></div></div></div>
    </aside>
  </>;
}
