/**
 * AdminSidebar — role-aware navigation sidebar.
 *
 * store_owner / store_manager: Dashboard, Orders, Products, Customers,
 *                               Analytics, Settings
 * platform_admin:              Stores, Analytics, Plans, System Health
 *
 * Mobile: hamburger toggle, collapses to off-canvas drawer at <768px.
 * All nav items: min 48×48px tap targets (AC8).
 *
 * Implementation: Story 1.8
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { UserRole } from "@/types/auth";

interface NavItem {
  label: string;
  href: string;
}

const STORE_NAV: NavItem[] = [
  { label: "Dashboard", href: "/dashboard/" },
  { label: "Orders", href: "/orders/" },
  { label: "Products", href: "/products/" },
  { label: "Customers", href: "/customers/" },
  { label: "Analytics", href: "/analytics/" },
  { label: "Settings", href: "/settings/" },
];

const PLATFORM_NAV: NavItem[] = [
  { label: "Stores", href: "/platform/" },
  { label: "Analytics", href: "/platform/analytics/" },
  { label: "Plans", href: "/platform/plans/" },
  { label: "System Health", href: "/platform/health/" },
];

interface AdminSidebarProps {
  role: UserRole;
  isOpen: boolean;
  onClose: () => void;
}

export default function AdminSidebar({
  role,
  isOpen,
  onClose,
}: AdminSidebarProps) {
  const pathname = usePathname();
  const navItems = role === "platform_admin" ? PLATFORM_NAV : STORE_NAV;

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={[
          "fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-gray-900 text-white transition-transform duration-200",
          "md:static md:translate-x-0 md:flex-shrink-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
        aria-label="Sidebar navigation"
      >
        {/* Brand */}
        <div className="flex h-16 items-center border-b border-gray-700 px-5">
          <span className="text-lg font-bold tracking-tight">joat stores</span>
        </div>

        {/* Nav items */}
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-3">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/" && pathname.startsWith(item.href));
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onClose}
                    className={[
                      // AC8: min 48px tap target (py-3 = 12px × 2 + text ≈ 48px)
                      "flex min-h-[48px] items-center rounded-lg px-3 py-3 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-gray-700 text-white"
                        : "text-gray-300 hover:bg-gray-800 hover:text-white",
                    ].join(" ")}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>
    </>
  );
}
