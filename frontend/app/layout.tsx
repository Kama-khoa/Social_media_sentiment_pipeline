import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";

const jakarta = Plus_Jakarta_Sans({ subsets: ["latin", "vietnamese"], variable: "--font-jakarta", display: "swap" });
const space = Space_Grotesk({ subsets: ["latin", "vietnamese"], variable: "--font-space", display: "swap" });

export const metadata: Metadata = {
  title: "TechChoice — Khám phá đánh giá công nghệ",
  description: "Hệ thống phân tích sentiment từ bình luận YouTube",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" data-theme="light" className={`${jakarta.variable} ${space.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
