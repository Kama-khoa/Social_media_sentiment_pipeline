"use client";

import { useAuth } from "@/lib/auth-context";
import { UserDashboard } from "@/components/dashboard/UserDashboard";
import { AdminDashboard } from "@/components/dashboard/AdminDashboard";

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) return null;

  return user.role === "admin" ? <AdminDashboard /> : <UserDashboard />;
}
