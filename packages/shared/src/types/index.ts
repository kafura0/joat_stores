// ── Domain types ────────────────────────────────────────────────────────────

export type TenantType = "retail" | "restaurant" | "bar" | "contracting";

export type UserRole =
  | "platform_admin"
  | "store_owner"
  | "store_manager"
  | "cashier"
  | "waiter";

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "fulfilled"
  | "completed"
  | "cancelled";

export type PaymentMethod = "cash" | "mpesa" | "card";
export type PaymentStatus = "pending" | "confirmed" | "failed" | "refunded";

// ── Auth types ──────────────────────────────────────────────────────────────

export interface IUser {
  id: string;
  email: string;
  role: UserRole;
  store_id: string | null;
  store_name?: string | null;
}

export interface ILoginCredentials {
  email: string;
  password: string;
}

export interface ITokenResponse {
  access: string;
  role: UserRole;
  store_id: string | null;
}

export interface IJWTPayload {
  user_id: string;
  email?: string;
  role: UserRole;
  store_id: string | null;
  exp: number;
  iat: number;
  token_type: "access";
}

// ── Store types ─────────────────────────────────────────────────────────────

export interface IStore {
  id: number;
  name: string;
  slug: string;
  domain: string;
  tenant_type: TenantType;
  is_active: boolean;
  created_at: string;
}

// ── Product types ───────────────────────────────────────────────────────────

export interface ICategory {
  id: number;
  name: string;
  description: string;
  parent: number | null;
  position: number;
  product_count?: number;
}

export interface IVariant {
  id: number;
  product: number;
  attribute_values: Record<string, string>;
  price: string;
  inventory_count: number;
  is_available: boolean;
  sku: string;
}

export interface IProductImage {
  id: number;
  image: string;
  alt_text: string;
  position: number;
  is_default: boolean;
}

export interface IProduct {
  id: number;
  name: string;
  description: string;
  category: ICategory | null;
  category_id: number | null;
  attribute_names: string[];
  is_available: boolean;
  variants: IVariant[];
  images: IProductImage[];
  created_at: string;
  updated_at: string;
}

// ── Order types ─────────────────────────────────────────────────────────────

export interface IOrderItem {
  id: number;
  variant: IVariant;
  variant_id: number;
  product_name: string;
  quantity: number;
  unit_price: string;
  total: string;
  modifiers?: Record<string, unknown>;
}

export interface IOrder {
  id: string;
  order_reference: string;
  status: OrderStatus;
  customer: ICustomer | null;
  customer_id: number | null;
  subtotal: string;
  tax_amount: string;
  total: string;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  items: IOrderItem[];
  notes: string;
  created_at: string;
  updated_at: string;
  served_by?: string;
}

export interface ICartItem {
  id: number;
  variant_id: number;
  product_name: string;
  variant_name: string;
  price: string;
  quantity: number;
  modifiers?: Record<string, unknown>;
}

// ── Customer types ──────────────────────────────────────────────────────────

export interface ICustomer {
  id: number;
  name: string;
  email: string;
  phone: string;
  total_orders: number;
  total_spent: string;
  created_at: string;
}

// ── Staff types ─────────────────────────────────────────────────────────────

export interface IStaff {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  last_login: string | null;
}

// ── Dashboard types ─────────────────────────────────────────────────────────

export interface IDashboardStats {
  today_revenue: string;
  today_transactions: number;
  today_avg_order: string;
  month_revenue: string;
  month_transactions: number;
  total_products: number;
  low_stock_count: number;
  active_customers: number;
  recent_orders: IOrder[];
  top_products: ITopProduct[];
}

export interface ITopProduct {
  product_name: string;
  quantity_sold: number;
  revenue: string;
}

// ── Inventory types ─────────────────────────────────────────────────────────

export interface IInventoryItem {
  variant_id: number;
  product_name: string;
  variant_name: string;
  sku: string;
  current_stock: number;
  low_stock_threshold: number;
  status: "in_stock" | "low_stock" | "out_of_stock";
}

// ── Menu types (restaurant / bar) ───────────────────────────────────────────

export interface IModifier {
  id: string;
  name: string;
  price_addition: string;
  is_available: boolean;
}

export interface IModifierGroup {
  id: string;
  name: string;
  min_selections: number;
  max_selections: number;
  is_required: boolean;
  modifiers: IModifier[];
}

export interface IMenuItem {
  id: string;
  name: string;
  description: string;
  price: string;
  contains_allergens: boolean;
  allergen_description: string;
  modifier_groups: IModifierGroup[];
}

export interface IMenuSection {
  id: string;
  name: string;
  description: string;
  items: IMenuItem[];
}

// ── Theme types ─────────────────────────────────────────────────────────────

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

// ── API response types ──────────────────────────────────────────────────────

export interface IApiResponse<T> {
  data: T;
}

export interface IApiListResponse<T> {
  data: T[];
  meta: {
    count: number;
    next: string | null;
    previous: string | null;
  };
}

export interface IApiError {
  field: string | null;
  message: string;
  code: string;
}

export interface IApiErrorResponse {
  errors: IApiError[];
}
