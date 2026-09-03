"use client";

import { useRouter } from "next/navigation";
import { Moon, Sun } from "lucide-react";
import { performLogout } from "@/lib/auth";
import { useAuthStore } from "@/stores/authStore";
import { useThemeStore } from "@/stores/themeStore";

interface AdminHeaderProps {
  onMenuToggle: () => void;
}

export default function AdminHeader({ onMenuToggle }: AdminHeaderProps) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const { isDark, toggle } = useThemeStore();

  const storeName =
    user?.role === "platform_admin"
      ? "Platform Admin"
      : (user?.store_name ?? "My Store");

  async function handleLogout() {
    await performLogout();
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] px-4 backdrop-blur-md sm:px-6">
      {/* Hamburger (mobile only) */}
      <button
        type="button"
        onClick={onMenuToggle}
        className="flex min-h-[48px] min-w-[48px] items-center justify-center rounded-xl text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-variant)] md:hidden"
        aria-label="Open sidebar"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Store name — gradient text */}
      <span className="text-sm font-semibold bg-gradient-to-r from-[var(--md-primary)] to-[var(--md-tertiary)] bg-clip-text text-transparent md:text-base">
        {storeName}
      </span>

      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          type="button"
          onClick={toggle}
          className="flex min-h-[48px] min-w-[48px] items-center justify-center rounded-xl text-[var(--md-on-surface-variant)] hover:bg-[var(--md-surface-variant)]"
          aria-label="Toggle theme"
        >
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>

        {/* Logout button */}
        <button
          type="button"
          onClick={handleLogout}
          className="flex min-h-[48px] items-center rounded-xl border border-[var(--md-outline)] px-4 text-sm font-medium text-[var(--md-on-surface)] transition-colors hover:bg-[var(--md-surface-variant)]"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
