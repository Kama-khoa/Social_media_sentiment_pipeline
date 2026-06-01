import { Navbar } from "@/components/public/Navbar";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-900">
      <Navbar />
      <main className="pt-14">{children}</main>
    </div>
  );
}
