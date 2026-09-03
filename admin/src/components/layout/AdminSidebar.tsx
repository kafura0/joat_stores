"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  Tags,
  Box,
  Receipt,
  Users,
  UserCog,
  BarChart3,
  Settings,
  Store,
} from "lucide-react";
import type { UserRole } from "@/types/auth";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ size?: number }>;
}

const STORE_OWNER_NAV: NavItem[] = [
  { label: "Dashboard", href: "/dashboard/", icon: LayoutDashboard },
  { label: "POS Terminal", href: "/pos/", icon: ShoppingCart },
  { label: "Products", href: "/products/", icon: Package },
  { label: "Categories", href: "/categories/", icon: Tags },
  { label: "Inventory", href: "/inventory/", icon: Box },
  { label: "Orders", href: "/orders/", icon: Receipt },
  { label: "Customers", href: "/customers/", icon: Users },
  { label: "Staff", href: "/staff/", icon: UserCog },
  { label: "Reports", href: "/reports/", icon: BarChart3 },
  { label: "Settings", href: "/settings/", icon: Settings },
];

const CASHIER_NAV: NavItem[] = [
  { label: "Dashboard", href: "/dashboard/", icon: LayoutDashboard },
  { label: "POS Terminal", href: "/pos/", icon: ShoppingCart },
  { label: "Orders", href: "/orders/", icon: Receipt },
];

const WAITER_NAV: NavItem[] = [
  { label: "Dashboard", href: "/waiter/", icon: LayoutDashboard },
  { label: "My Sales", href: "/waiter/my-sales/", icon: BarChart3 },
];

const PLATFORM_NAV: NavItem[] = [
  { label: "Overview", href: "/platform/", icon: LayoutDashboard },
  { label: "Stores", href: "/platform/stores/", icon: Store },
  { label: "Users", href: "/platform/users/", icon: Users },
  { label: "Settings", href: "/platform/settings/", icon: Settings },
];

function getNavForRole(role: UserRole): NavItem[] {
  switch (role) {
    case "platform_admin":
      return PLATFORM_NAV;
    case "store_owner":
    case "store_manager":
      return STORE_OWNER_NAV;
    case "cashier":
      return CASHIER_NAV;
    case "waiter":
      return WAITER_NAV;
    default:
      return STORE_OWNER_NAV;
  }
}

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
  const navItems = getNavForRole(role);

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={[
          "fixed inset-y-0 left-0 z-30 flex flex-col transition-transform duration-200",
          "w-[280px] bg-[var(--md-surface)] border-r border-[var(--md-outline-variant)]",
          "md:static md:translate-x-0 md:flex-shrink-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
        aria-label="Sidebar navigation"
      >
        {/* Brand header — gradient text like template */}
        <div className="flex h-16 items-center border-b border-[var(--md-outline-variant)] px-6">
          <div className="flex flex-col">
            <span className="text-lg font-bold bg-gradient-to-r from-[var(--md-primary)] to-[var(--md-tertiary)] bg-clip-text text-transparent">
              joat stores
            </span>
            <span className="text-xs text-[var(--md-on-surface-variant)]">
              {role === "platform_admin" ? "Platform Admin" : "Store Dashboard"}
            </span>
          </div>
        </div>

        {/* Navigation — glassmorphism hover effects */}
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-3">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/" &&
                  pathname.startsWith(item.href) &&
                  !navItems.some(
                    (other) =>
                      other.href !== item.href &&
                      other.href.length > item.href.length &&
                      pathname.startsWith(other.href)
                  ));
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onClose}
                    className={[
                      "flex min-h-[48px] items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200",
                      isActive
                        ? "bg-[var(--md-primary-container)] text-[var(--md-on-primary-container)] shadow-[var(--shadow-subtle)]"
                        : "text-[var(--md-on-surface-variant)] hover:bg-[var(--glass-bg)] hover:backdrop-blur-md hover:text-[var(--md-on-surface)] hover:shadow-[var(--shadow-subtle)]",
                    ].join(" ")}
                  >
                    <item.icon size={20} />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* User profile footer */}
        <div className="border-t border-[var(--md-outline-variant)] p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--md-primary-container)] text-[var(--md-on-primary-container)] text-sm font-bold">
              A
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-medium text-[var(--md-on-surface)] truncate">
                Store Admin
              </span>
              <span className="text-xs text-[var(--md-on-surface-variant)] truncate">
                admin@joat.com
              </span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
