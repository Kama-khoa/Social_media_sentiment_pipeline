"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/analytics/top-products", label: "Bảng xếp hạng" },
  { href: "/analytics/search", label: "Tìm kiếm" },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 bg-slate-900 border-b border-slate-700/60 flex items-center px-6">
      <Link
        href="/analytics/top-products"
        className="text-cyan-400 font-bold text-lg tracking-tight mr-10 hover:text-cyan-300 transition-colors"
      >
        SentimentIQ
      </Link>

      <div className="flex items-center gap-1 flex-1">
        {NAV_LINKS.map((link) => {
          const active = pathname.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                active
                  ? "text-cyan-400 bg-cyan-500/10"
                  : "text-slate-300 hover:text-cyan-400 hover:bg-slate-800"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </div>

      <Link
        href="/login"
        className="px-4 py-1.5 rounded-md text-sm font-medium bg-violet-600 hover:bg-violet-500 text-white transition-colors"
      >
        Quản trị
      </Link>
    </nav>
  );
}
