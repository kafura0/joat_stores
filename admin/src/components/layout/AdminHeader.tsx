/**
 * AdminHeader — top bar with store name + Logout button.
 *
 * Implementation: Story 1.8
 */

"use client";

import { useRouter } from "next/navigation";

import { performLogout } from "@/lib/auth";
import { useAuthStore } from "@/stores/authStore";

interface AdminHeaderProps {
  onMenuToggle: () => void;
}

export default function AdminHeader({ onMenuToggle }: AdminHeaderProps) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  // TODO (Epic 4): Replace stub with real store_name fetched from store detail API.
  // store_name is not in the JWT payload; IUser.store_name is populated once
  // the store detail endpoint (/api/v1/stores/{id}/) is built in Epic 4.
  const storeName =
    user?.role === "platform_admin"
      ? "Platform Admin"
      : (user?.store_name ?? "My Store");

  async function handleLogout() {
    await performLogout();
    router.push("/login");
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 sm:px-6">
      {/* Hamburger (mobile only) */}
      <button
        type="button"
        onClick={onMenuToggle}
        className="flex min-h-[48px] min-w-[48px] items-center justify-center rounded-md text-gray-500 hover:bg-gray-100 md:hidden"
        aria-label="Open sidebar"
      >
        {/* Hamburger icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="22"
          height="22"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Store name */}
      <span className="text-sm font-semibold text-gray-700 md:text-base">
        {storeName}
      </span>

      {/* Logout button — AC6 */}
      <button
        type="button"
        onClick={handleLogout}
        className="flex min-h-[48px] items-center rounded-lg border border-gray-300 px-4 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
      >
        Logout
      </button>
    </header>
  );
}
