"use client";

import { useEffect } from "react";
import { useThemeStore } from "@/stores/themeStore";

export default function POSLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isDark, setDark } = useThemeStore();

  // POS is always dark mode
  useEffect(() => {
    if (!isDark) setDark(true);
  }, [isDark, setDark]);

  return <div className="flex h-screen flex-col bg-[var(--md-surface)]">{children}</div>;
}
