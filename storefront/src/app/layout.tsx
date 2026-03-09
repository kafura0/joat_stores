import type { Metadata } from "next";
import TenantThemeProvider from "@/components/layout/TenantThemeProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "joat_stores",
  description: "Your store",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <TenantThemeProvider>{children}</TenantThemeProvider>
      </body>
    </html>
  );
}
