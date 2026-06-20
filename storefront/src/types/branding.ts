export interface ThemeData {
  preset_slug: string;
  template_style: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  background_color: string;
  surface_color: string;
  text_primary_color: string;
  text_secondary_color: string;
  success_color: string;
  error_color: string;
  warning_color: string;
  header_background: string;
  header_text_color: string;
  footer_background: string;
  footer_text_color: string;
  font_family_heading: string;
  font_family_body: string;
  font_size_base: string;
  font_size_scale: number;
  section_padding_y: string;
  card_padding: string;
  container_max_width: string;
  radius_sm: string;
  radius_md: string;
  radius_lg: string;
  radius_full: string;
  shadow_sm: string;
  shadow_md: string;
  shadow_lg: string;
  announcement_enabled: boolean;
  announcement_text: string;
  custom_css: string;
}

export interface BrandingData {
  store_name: string;
  logo_url: string;
  tagline: string;
  currency: string;
  country: string;
  status: "pending" | "active" | "suspended" | "cancelled";
  theme: ThemeData;
  powered_by: {
    text: string;
    url: string;
    logo_url: string;
  };
}

export const DEFAULT_THEME: ThemeData = {
  preset_slug: "modern",
  template_style: "modern",
  primary_color: "#1a1a1a",
  secondary_color: "#6b7280",
  accent_color: "#e63946",
  background_color: "#ffffff",
  surface_color: "#f9fafb",
  text_primary_color: "#111827",
  text_secondary_color: "#6b7280",
  success_color: "#16a34a",
  error_color: "#dc2626",
  warning_color: "#f59e0b",
  header_background: "#1a1a1a",
  header_text_color: "#ffffff",
  footer_background: "#1f2937",
  footer_text_color: "#f3f4f6",
  font_family_heading: "Inter",
  font_family_body: "Inter",
  font_size_base: "1rem",
  font_size_scale: 1.25,
  section_padding_y: "4rem",
  card_padding: "1.5rem",
  container_max_width: "1280px",
  radius_sm: "0.25rem",
  radius_md: "0.5rem",
  radius_lg: "0.75rem",
  radius_full: "9999px",
  shadow_sm: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
  shadow_md: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
  shadow_lg: "0 10px 15px -3px rgb(0 0 0 / 0.1)",
  announcement_enabled: false,
  announcement_text: "",
  custom_css: "",
};

export const DEFAULT_BRANDING: BrandingData = {
  store_name: "joat stores",
  logo_url: "",
  tagline: "",
  currency: "KES",
  country: "KE",
  status: "active",
  theme: DEFAULT_THEME,
  powered_by: {
    text: "Powered by joat stores",
    url: "https://joat.com",
    logo_url: "https://joat.com/static/logo-small.svg",
  },
};
