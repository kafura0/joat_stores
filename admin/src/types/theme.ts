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

export interface PresetItem {
  slug: string;
  label: string;
  description: string;
  thumbnail_url: string | null;
}

export const FONT_OPTIONS = [
  "Inter",
  "Roboto",
  "Lora",
  "Merriweather",
  "Poppins",
  "Space Grotesk",
  "Playfair Display",
  "DM Sans",
  "Nunito",
  "Work Sans",
  "Outfit",
  "Plus Jakarta Sans",
] as const;

export const COLOR_LABELS: Record<string, string> = {
  primary_color: "Primary",
  secondary_color: "Secondary",
  accent_color: "Accent",
  background_color: "Background",
  surface_color: "Surface",
  text_primary_color: "Text Primary",
  text_secondary_color: "Text Secondary",
  success_color: "Success",
  error_color: "Error",
  warning_color: "Warning",
  header_background: "Header BG",
  header_text_color: "Header Text",
  footer_background: "Footer BG",
  footer_text_color: "Footer Text",
};
