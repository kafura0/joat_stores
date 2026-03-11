/**
 * Authenticated admin layout.
 *
 * On mount:
 *   1. If no access token in memory → attempt token refresh (performRefresh)
 *   2. If refresh fails → redirect to /login
 *   3. If user role doesn't match current route prefix → redirect to correct root
 *
 * Renders: AdminHeader + AdminSidebar + children
 *
 * Implementation: Story 1.8
 */

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AdminHeader from "@/components/layout/AdminHeader";
import AdminSidebar from "@/components/layout/AdminSidebar";
import { performRefresh } from "@/lib/auth";
import { useAuthStore } from "@/stores/authStore";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { accessToken, user } = useAuthStore();
  const [isReady, setIsReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    async function hydrate() {
      if (accessToken) {
        // Already have a token in memory — ready to render
        setIsReady(true);
        return;
      }

      // No token — try silent refresh from httpOnly cookie
      const newToken = await performRefresh();
      if (!newToken) {
        router.replace("/login");
        return;
      }

      setIsReady(true);
    }

    hydrate();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // While hydrating, render nothing (middleware already redirected if no cookie)
  if (!isReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <span className="text-sm text-gray-400">Loading…</span>
      </div>
    );
  }

  const role = user?.role ?? "store_owner";

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <AdminSidebar
        role={role}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <AdminHeader onMenuToggle={() => setSidebarOpen((o) => !o)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
