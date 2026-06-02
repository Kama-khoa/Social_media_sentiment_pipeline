import { GuestHeader } from "@/components/layout/GuestHeader";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <GuestHeader title="TechChoice" />
      {children}
    </div>
  );
}
