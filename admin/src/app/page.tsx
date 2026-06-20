/**
 * Root page — role-based redirect after authentication.
 *
 * - If authenticated: redirect to /platform/ (platform_admin) or /dashboard/
 * - If not authenticated: redirect to /login (middleware handles this, but
 *   also handled here as belt-and-suspenders)
 *
 * Implementation: Story 1.8
 */

"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { performRefresh } from "@/lib/auth";
import { useAuthStore } from "@/stores/authStore";

export default function RootPage() {
  const router = useRouter();

  useEffect(() => {
    async function redirect() {
      const { accessToken, user } = useAuthStore.getState();
      let role = user?.role;

      if (!accessToken || !role) {
        const newToken = await performRefresh();
        if (!newToken) {
          router.replace("/login");
          return;
        }
        role = useAuthStore.getState().user?.role;
      }

      if (role === "platform_admin") {
        router.replace("/platform/");
      } else {
        router.replace("/dashboard/");
      }
    }

    redirect();
  }, [router])

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <span className="text-sm text-gray-400">Redirecting…</span>
    </div>
  );
}
