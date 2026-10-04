"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { fetchUser, user, isLoading, isAuthenticated } = useAuthStore();

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) router.push("/login");
      else if (user && user.role !== "admin" && user.role !== "superadmin") {
        router.push("/dashboard");
      }
    }
  }, [isLoading, isAuthenticated, user, router]);

  if (isLoading) return null;
  return <>{children}</>;
}
