"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AdminHeader from "@/components/layout/AdminHeader";
import AdminSidebar from "@/components/layout/AdminSidebar";
import { performRefresh } from "@/lib/auth";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const [isReady, setIsReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isDark } = useThemeStore();

  useEffect(() => {
    async function hydrate() {
      const { accessToken } = useAuthStore.getState();
      if (accessToken) {
        setIsReady(true);
        return;
      }

      const newToken = await performRefresh();
      if (!newToken) {
        router.replace("/login");
        return;
      }

      setIsReady(true);
    }

    hydrate();
  }, [router]);

  // Apply theme class on mount
  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);

  if (!isReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--md-surface)]">
        <span className="text-sm text-[var(--md-on-surface-variant)]">Loading...</span>
      </div>
    );
  }

  const role = user?.role ?? "store_owner";

  return (
    <div className={`flex min-h-screen bg-[var(--md-surface)] ${isDark ? "dark" : ""}`}>
      <AdminSidebar
        role={role}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <AdminHeader onMenuToggle={() => setSidebarOpen((o) => !o)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
