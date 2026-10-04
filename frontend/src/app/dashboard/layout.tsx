"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { DashboardSidebar } from "@/components/dashboard/sidebar";
import { useAuthStore } from "@/store/auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { fetchUser, isAuthenticated, isLoading } = useAuthStore();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />
      <main className="ml-64 min-h-screen p-8">{children}</main>
    </div>
  );
}
