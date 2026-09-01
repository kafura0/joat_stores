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

export interface IStore {
  id: number;
  name: string;
  slug: string;
  domain: string;
  tenant_type: TenantType;
  is_active: boolean;
  created_at: string;
}

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

export interface ICustomer {
  id: number;
  name: string;
  email: string;
  phone: string;
  total_orders: number;
  total_spent: string;
  created_at: string;
}

export interface IStaff {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  last_login: string | null;
}

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

export interface IInventoryItem {
  variant_id: number;
  product_name: string;
  variant_name: string;
  sku: string;
  current_stock: number;
  low_stock_threshold: number;
  status: "in_stock" | "low_stock" | "out_of_stock";
}

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
