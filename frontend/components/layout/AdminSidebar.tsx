"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon, type IconName } from "@/components/shared/Icon";

interface AdminSidebarProps {
  open: boolean;
  onClose: () => void;
}

const items: Array<{ href: string; label: string; icon: IconName }> = [
  { href: "/admin", label: "Tổng quan phân tích", icon: "grid" },
  { href: "/admin/channels", label: "Quản lý kênh", icon: "broadcast" },
  { href: "/admin/keywords", label: "Quản lý từ khóa", icon: "tag" },
  { href: "/admin/products", label: "Quản lý sản phẩm", icon: "box" },
  { href: "/admin/airflow", label: "Tình trạng Pipeline", icon: "heart" },
  { href: "/admin/airflow#runs", label: "Lịch sử DAG Runs", icon: "flow" },
  { href: "/admin#ops", label: "Chỉ số vận hành", icon: "activity" },
];

export function AdminSidebar({ open, onClose }: AdminSidebarProps) {
  const pathname = usePathname();
  return <>
    {open && <button className="admin-sidebar-scrim fixed inset-0 z-[60] hidden bg-[#140c2880]" onClick={onClose} aria-label="Đóng menu" />}
    <aside className={`admin-sidebar fixed inset-y-0 left-0 z-[70] flex w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] lg:sticky lg:top-0 lg:z-30 lg:h-screen lg:translate-x-0 ${open ? "open" : ""}`}>
      <Link href="/admin" className="flex items-center gap-[11px] px-5 pb-3.5 pt-5">
        <span className="grid h-[34px] w-[34px] place-items-center rounded-[10px] bg-gradient-to-br from-[var(--v-500)] to-[var(--v-700)] text-white"><Icon name="spark" size={19} /></span>
        <span><span className="block text-base font-extrabold tracking-[-.02em]">TechChoice</span><span className="faint block text-[11px] font-semibold tracking-[.04em]">BẢNG QUẢN TRỊ</span></span>
      </Link>
      <nav className="flex-1 overflow-y-auto px-3 py-1.5">
        <div className="faint px-3 pb-2 pt-3 text-[11px] font-bold tracking-[.06em]">ĐIỀU HƯỚNG</div>
        {items.map((item) => {
          const active = item.href === "/admin" ? pathname === "/admin" : pathname === item.href.split("#")[0];
          return <Link key={item.label} href={item.href} onClick={onClose} className={`relative mb-0.5 flex items-center gap-[11px] rounded-[10px] px-3 py-2.5 text-sm font-semibold transition-all ${active ? "bg-[var(--primary-soft)] text-[var(--primary)]" : "text-[var(--text-2)] hover:bg-[var(--surface-3)] hover:text-[var(--text)]"}`}>{active && <span className="absolute bottom-2 left-0 top-2 w-[3px] rounded-full bg-[var(--primary)]" />}<Icon name={item.icon} size={18} />{item.label}</Link>;
        })}
      </nav>
      <div className="border-t border-[var(--border)] p-3.5"><div className="card flex items-center gap-2.5 bg-[var(--surface-2)] p-3"><span className="h-2 w-2 rounded-full bg-[var(--pos)] [animation:pulseDot_1.4s_infinite]" /><div className="text-xs"><div className="font-bold">Hệ thống ổn định</div><div className="faint">Airflow · BigQuery · Redis</div></div></div></div>
    </aside>
  </>;
}
