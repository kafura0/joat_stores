import { headers } from "next/headers";
import React from "react";

import { DynamicHeader, DynamicFooter } from "@/components/layout/variants/resolveVariant";
import { fetchTenantBranding } from "@/lib/branding";
import { DEFAULT_BRANDING } from "@/types/branding";
import SuspendedPage from "@/app/suspended/page";

function buildCssVars(branding: typeof DEFAULT_BRANDING): React.CSSProperties {
  const t = branding.theme;
  return {
    "--color-primary": t.primary_color,
    "--color-secondary": t.secondary_color,
    "--color-accent": t.accent_color,
    "--color-background": t.background_color,
    "--color-surface": t.surface_color,
    "--color-text-primary": t.text_primary_color,
    "--color-text-secondary": t.text_secondary_color,
    "--color-success": t.success_color,
    "--color-error": t.error_color,
    "--color-warning": t.warning_color,
    "--header-bg": t.header_background,
    "--header-text": t.header_text_color,
    "--footer-bg": t.footer_background,
    "--footer-text": t.footer_text_color,
    "--font-heading": `${t.font_family_heading}, sans-serif`,
    "--font-body": `${t.font_family_body}, sans-serif`,
    "--section-padding-y": t.section_padding_y,
    "--card-padding": t.card_padding,
    "--container-max-width": t.container_max_width,
    "--radius-sm": t.radius_sm,
    "--radius-md": t.radius_md,
    "--radius-lg": t.radius_lg,
    "--radius-full": t.radius_full,
    "--shadow-sm": t.shadow_sm,
    "--shadow-md": t.shadow_md,
    "--shadow-lg": t.shadow_lg,
  } as React.CSSProperties;
}

export default async function TenantThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const headersList = await headers();
  const hostname = headersList.get("host") ?? "localhost";

  const branding = await fetchTenantBranding(hostname);
  const cssVariables = buildCssVars(branding);

  const shell = (content: React.ReactNode) => (
    <div style={cssVariables} className="flex min-h-screen flex-col">
      {branding.theme.announcement_enabled && branding.theme.announcement_text && (
        <div
          className="w-full px-4 py-2 text-center text-sm font-medium"
          style={{
            backgroundColor: "var(--color-accent)",
            color: "#ffffff",
          }}
        >
          {branding.theme.announcement_text}
        </div>
      )}
      {branding.theme.custom_css && (
        <style>{branding.theme.custom_css}</style>
      )}
      {content}
    </div>
  );

  if (branding.status === "suspended") {
    return shell(
      <>
        <DynamicHeader branding={branding} templateStyle={branding.theme.template_style} />
        <main className="flex flex-1 items-center justify-center px-4">
          <SuspendedPage />
        </main>
        <DynamicFooter branding={branding} templateStyle={branding.theme.template_style} />
      </>
    );
  }

  return shell(
    <>
      <DynamicHeader branding={branding} templateStyle={branding.theme.template_style} />
      <main className="flex-1">{children}</main>
      <DynamicFooter branding={branding} templateStyle={branding.theme.template_style} />
    </>
  );
}
