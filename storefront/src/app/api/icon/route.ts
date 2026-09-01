import { NextRequest, NextResponse } from "next/server";

import { fetchTenantBranding } from "@/lib/branding";

/**
 * Dynamic icon endpoint — redirects to the store's logo,
 * or generates a simple SVG fallback with the store's initial.
 *
 * GET /api/icon
 */
export async function GET(request: NextRequest) {
  const hostname = request.headers.get("host") ?? "localhost";
  const branding = await fetchTenantBranding(hostname);

  const logoUrl = branding.logo_url;

  // If store has a logo, redirect to it
  if (logoUrl) {
    return NextResponse.redirect(logoUrl, {
      headers: {
        "Cache-Control": "public, max-age=86400, s-maxage=86400",
      },
    });
  }

  // Fallback: generate SVG with store initial
  const initial = (branding.store_name || "J").charAt(0).toUpperCase();
  const bgColor = branding.theme?.primary_color || "#1a1a1a";
  const textColor = branding.theme?.header_text_color || "#ffffff";

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
      <rect width="512" height="512" rx="96" fill="${bgColor}"/>
      <text x="256" y="300" font-family="Inter, system-ui, sans-serif" font-size="280" font-weight="700" fill="${textColor}" text-anchor="middle">${initial}</text>
    </svg>
  `;

  return new NextResponse(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=86400, s-maxage=86400",
    },
  });
}
