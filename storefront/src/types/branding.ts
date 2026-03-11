/**
 * Branding data returned by GET /api/v1/store/branding/
 * Implementation: Story 1.7
 */
export interface BrandingData {
  store_name: string;
  logo_url: string;
  tagline: string;
  primary_color: string;
  secondary_color: string;
  font_family: string;
  currency: string;
  country: string;
  status: "pending" | "active" | "suspended" | "cancelled";
}

export const DEFAULT_BRANDING: BrandingData = {
  store_name: "joat stores",
  logo_url: "",
  tagline: "",
  primary_color: "#1a1a1a",
  secondary_color: "#6b7280",
  font_family: "Inter",
  currency: "KES",
  country: "KE",
  status: "active",
};
