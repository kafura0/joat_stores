# StoreSphere — Frontend Scaffold Prompt

> **Purpose:** This prompt generates the complete Next.js 16 admin dashboard for a bar + restaurant SaaS POS. Copy-paste into any AI coding assistant (Cursor, Copilot, Claude, Gemini, Google Stitch) to scaffold all pages, components, types, stores, and API integrations.

---

## System Context

You are building a multi-tenant SaaS e-commerce platform called **JOAT Stores** for Kenyan SMEs. The backend is Django 5.2 + DRF, already deployed at `https://joat-stores-api-qtde.onrender.com`. The admin frontend is Next.js 16 (App Router) deployed at `https://joat-stores-admin.vercel.app`.

**Stack:**
- Next.js 16, App Router, TypeScript strict mode
- Tailwind CSS
- Zustand (UI state)
- TanStack Query (server state)
- react-hook-form + zod (forms)
- axios (API client — already configured in `src/lib/api.ts`)

**First client:** A bar + restaurant combo business in Kenya.

---

## Architecture

``` 
admin/src/
├── app/
│   ├── (admin)/                    # Store owner / manager views
│   │   ├── layout.tsx              # ✅ EXISTS — authenticated shell with sidebar
│   │   ├── dashboard/page.tsx      # 🔄 REPLACE — full dashboard with stats
│   │   ├── products/page.tsx       # 🆕 Product list + CRUD
│   │   ├── products/[id]/page.tsx  # 🆕 Product detail/edit
│   │   ├── categories/page.tsx     # 🆕 Category management
│   │   ├── inventory/page.tsx      # 🆕 Stock overview
│   │   ├── orders/page.tsx         # 🆕 Order/transaction history
│   │   ├── orders/[id]/page.tsx    # 🆕 Order detail
│   │   ├── customers/page.tsx      # 🆕 Customer list
│   │   ├── customers/[id]/page.tsx # 🆕 Customer detail
│   │   ├── staff/page.tsx          # 🆕 Staff management
│   │   ├── reports/page.tsx        # 🆕 Basic reports
│   │   └── settings/page.tsx       # 🔄 REPLACE — store settings
│   ├── (pos)/                      # POS terminal views (touch-optimized)
│   │   ├── layout.tsx              # 🆕 POS layout (no sidebar, full-width)
│   │   └── page.tsx                # 🆕 POS terminal
│   ├── (waiter)/                   # Waiter mobile-first views
│   │   ├── layout.tsx              # 🆕 Waiter layout (minimal, mobile)
│   │   ├── page.tsx                # 🆕 Waiter dashboard / take order
│   │   └── my-sales/page.tsx       # 🆕 Waiter's daily sales
│   ├── platform/                   # ✅ EXISTS — platform admin
│   │   ├── page.tsx                # 🔄 REPLACE — platform overview
│   │   ├── stores/page.tsx         # 🆕 Store management
│   │   ├── users/page.tsx          # 🆕 User management
│   │   └── settings/page.tsx       # 🆕 Platform settings
│   ├── login/page.tsx              # ✅ EXISTS
│   └── page.tsx                    # ✅ EXISTS — root redirect
├── components/
│   ├── layout/
│   │   ├── AdminHeader.tsx         # ✅ EXISTS
│   │   ├── AdminSidebar.tsx        # 🔄 UPDATE — add POS/Waiter nav
│   │   └── POSLayout.tsx           # 🆕 POS-specific layout
│   ├── ui/                         # 🆕 Shared UI components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── DataTable.tsx
│   │   ├── Dialog.tsx
│   │   ├── Dropdown.tsx
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── Badge.tsx
│   │   ├── StatCard.tsx
│   │   └── LoadingSpinner.tsx
│   ├── dashboard/                  # 🆕 Dashboard widgets
│   │   ├── StatsGrid.tsx
│   │   ├── RecentOrders.tsx
│   │   ├── TopProducts.tsx
│   │   └── RevenueChart.tsx
│   ├── products/                   # 🆕 Product components
│   │   ├── ProductTable.tsx
│   │   ├── ProductForm.tsx
│   │   └── ProductCard.tsx
│   ├── pos/                        # 🆕 POS components
│   │   ├── ProductGrid.tsx
│   │   ├── Cart.tsx
│   │   ├── CartItem.tsx
│   │   ├── PaymentModal.tsx
│   │   ├── BarcodeScanner.tsx
│   │   └── ReceiptPreview.tsx
│   └── waiter/                     # 🆕 Waiter components
│       ├── WaiterOrderPad.tsx
│       └── WaiterSalesSummary.tsx
├── lib/
│   ├── api.ts                      # ✅ EXISTS — axios client
│   ├── auth.ts                     # ✅ EXISTS — login/logout/refresh
│   └── utils.ts                    # 🆕 formatCurrency, formatDate, etc.
├── stores/
│   ├── authStore.ts                # ✅ EXISTS
│   ├── cartStore.ts                # 🆕 POS cart state
│   └── uiStore.ts                  # 🆕 UI state (modals, toasts)
└── types/
    ├── index.ts                    # 🔄 EXPAND — all domain types
    ├── auth.ts                     # ✅ EXISTS
    └── product.ts                  # 🆕 Product-specific types
```

---

## Type Definitions

Generate these types in `src/types/index.ts`:

```typescript
// ── Store & Tenant ──────────────────────────────────────────────────────────
export interface IStore {
  id: number;
  name: string;
  slug: string;
  domain: string;
  tenant_type: "retail" | "restaurant" | "bar" | "contracting";
  is_active: boolean;
  created_at: string;
}

// ── User & Auth ─────────────────────────────────────────────────────────────
export type UserRole = "platform_admin" | "store_owner" | "store_manager" | "cashier" | "waiter";

export interface IUser {
  id: string;
  email: string;
  role: UserRole;
  store_id: number | null;
  first_name?: string;
  last_name?: string;
}

// ── Product ─────────────────────────────────────────────────────────────────
export interface ICategory {
  id: number;
  name: string;
  description: string;
  parent: number | null;
  position: number;
  product_count?: number;
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

export interface IVariant {
  id: number;
  product: number;
  attribute_values: Record<string, string>;
  price: string;  // Decimal string, never float
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

// ── Order ───────────────────────────────────────────────────────────────────
export type OrderStatus = "pending" | "confirmed" | "fulfilled" | "completed" | "cancelled";
export type PaymentMethod = "cash" | "mpesa" | "card";
export type PaymentStatus = "pending" | "confirmed" | "failed" | "refunded";

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
  served_by?: string;  // Waiter/cashier name
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

// ── Cart (POS) ──────────────────────────────────────────────────────────────
export interface ICartItem {
  variant_id: number;
  product_name: string;
  variant_name: string;
  price: string;
  quantity: number;
  modifiers?: Record<string, unknown>;
}

// ── Customer ────────────────────────────────────────────────────────────────
export interface ICustomer {
  id: number;
  name: string;
  email: string;
  phone: string;
  total_orders: number;
  total_spent: string;
  created_at: string;
}

// ── Staff ───────────────────────────────────────────────────────────────────
export interface IStaff {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_active: boolean;
  last_login: string | null;
}

// ── Dashboard ───────────────────────────────────────────────────────────────
export interface IDashboardStats {
  today_revenue: string;
  today_transactions: number;
  today_avg_order: string;
  month_revenue: string;
  month_transactions: number;
  total_products: number;
  low_stock_count: number;
  active_customers: number;
}

export interface ITopProduct {
  product_name: string;
  quantity_sold: number;
  revenue: string;
}

// ── Inventory ───────────────────────────────────────────────────────────────
export interface IInventoryItem {
  variant_id: number;
  product_name: string;
  variant_name: string;
  sku: string;
  current_stock: number;
  low_stock_threshold: number;
  status: "in_stock" | "low_stock" | "out_of_stock";
}

// ── API Response Wrappers ───────────────────────────────────────────────────
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
```

---

## Zustand Stores

### `src/stores/cartStore.ts` — POS Cart

```typescript
import { create } from "zustand";
import type { ICartItem } from "@/types";

interface CartState {
  items: ICartItem[];
  customer_id: number | null;
  payment_method: "cash" | "mpesa" | "card";
  discount: string;
  notes: string;

  addItem: (item: Omit<ICartItem, "quantity">) => void;
  removeItem: (variant_id: number) => void;
  updateQuantity: (variant_id: number, quantity: number) => void;
  clearCart: () => void;
  setCustomer: (id: number | null) => void;
  setPaymentMethod: (method: "cash" | "mpesa" | "card") => void;
  setDiscount: (discount: string) => void;
  setNotes: (notes: string) => void;

  // Computed
  subtotal: () => string;
  tax: () => string;
  total: () => string;
  itemCount: () => number;
}

export const useCartStore = create<CartState>((set, get) => ({
  items: [],
  customer_id: null,
  payment_method: "cash",
  discount: "0.00",
  notes: "",

  addItem: (item) =>
    set((state) => {
      const existing = state.items.find((i) => i.variant_id === item.variant_id);
      if (existing) {
        return {
          items: state.items.map((i) =>
            i.variant_id === item.variant_id
              ? { ...i, quantity: i.quantity + 1 }
              : i
          ),
        };
      }
      return { items: [...state.items, { ...item, quantity: 1 }] };
    }),

  removeItem: (variant_id) =>
    set((state) => ({
      items: state.items.filter((i) => i.variant_id !== variant_id),
    })),

  updateQuantity: (variant_id, quantity) =>
    set((state) => ({
      items:
        quantity <= 0
          ? state.items.filter((i) => i.variant_id !== variant_id)
          : state.items.map((i) =>
              i.variant_id === variant_id ? { ...i, quantity } : i
            ),
    })),

  clearCart: () => set({ items: [], customer_id: null, notes: "" }),
  setCustomer: (id) => set({ customer_id: id }),
  setPaymentMethod: (method) => set({ payment_method: method }),
  setDiscount: (discount) => set({ discount }),
  setNotes: (notes) => set({ notes }),

  subtotal: () => {
    const { items } = get();
    return items
      .reduce((sum, item) => sum + parseFloat(item.price) * item.quantity, 0)
      .toFixed(2);
  },

  tax: () => {
    // 16% VAT for Kenya
    const sub = parseFloat(get().subtotal());
    return (sub * 0.16).toFixed(2);
  },

  total: () => {
    const sub = parseFloat(get().subtotal());
    const tax = parseFloat(get().tax());
    const discount = parseFloat(get().discount);
    return (sub + tax - discount).toFixed(2);
  },

  itemCount: () => get().items.reduce((sum, item) => sum + item.quantity, 0),
}));
```

### `src/stores/uiStore.ts` — UI State

```typescript
import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  activeModal: string | null;
  toasts: Toast[];

  toggleSidebar: () => void;
  openModal: (id: string) => void;
  closeModal: () => void;
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

interface Toast {
  id: string;
  type: "success" | "error" | "info";
  message: string;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  activeModal: null,
  toasts: [],

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  openModal: (id) => set({ activeModal: id }),
  closeModal: () => set({ activeModal: null }),
  addToast: (toast) =>
    set((s) => ({
      toasts: [...s.toasts, { ...toast, id: Date.now().toString() }],
    })),
  removeToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
```

---

## Utility Functions

### `src/lib/utils.ts`

```typescript
import { format, parseISO } from "date-fns";

constformatter = new Intl.NumberFormat("en-KE", {
  style: "currency",
  currency: "KES",
  minimumFractionDigits: 2,
});

export function formatCurrency(amount: string | number): string {
  return formatter.format(typeof amount === "string" ? parseFloat(amount) : amount);
}

export function formatDate(dateString: string): string {
  return format(parseISO(dateString), "MMM dd, yyyy");
}

export function formatDateTime(dateString: string): string {
  return format(parseISO(dateString), "MMM dd, yyyy HH:mm");
}

export function formatTime(dateString: string): string {
  return format(parseISO(dateString), "HH:mm");
}

export function cn(...classes: (string | undefined | false)[]): string {
  return classes.filter(Boolean).join(" ");
}
```

---

## API Endpoints Reference

All endpoints use base URL: `https://joat-stores-api-qtde.onrender.com/api/v1`

| Module | Endpoint | Method | Description |
|--------|----------|--------|-------------|
| **Auth** | `/auth/token/` | POST | Login (email, password) → access token |
| | `/auth/token/refresh/` | POST | Refresh access token |
| **Products** | `/products/` | GET/POST | List/create products |
| | `/products/{id}/` | GET/PUT/PATCH/DELETE | Product CRUD |
| | `/categories/` | GET/POST | List/create categories |
| | `/categories/{id}/` | GET/PUT/PATCH/DELETE | Category CRUD |
| **Orders** | `/orders/{id}/` | GET | Order detail |
| | `/orders/{id}/status/` | GET | Order status |
| | `/orders/{id}/confirm/` | POST | Confirm order |
| **Cart** | `/cart/` | GET/POST/PUT/DELETE | Cart operations |
| | `/cart/merge/` | POST | Merge carts |
| **Checkout** | `/checkout/` | POST | Create order from cart |
| **Dashboard** | `/dashboard/` | GET | Merchant dashboard stats |
| **Customers** | `/customers/` | GET/POST | List/create customers |
| | `/customers/{id}/` | GET/PUT/PATCH/DELETE | Customer CRUD |
| **Inventory** | `/inventory/` | GET | Stock levels |
| | `/inventory/{id}/adjust/` | POST | Adjust stock |
| **Platform** | `/platform/stores/` | GET | All stores (admin) |
| | `/platform/users/` | GET | All users (admin) |

---

## Page Specifications

### 1. Dashboard (`/dashboard`)

**Layout:** Stats grid at top, recent orders table, top products sidebar.

```
┌─────────────────────────────────────────────────────────┐
│  TODAY                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Revenue  │ │ Orders   │ │ Avg Sale │ │ Products │  │
│  │ KSh 284K │ │ 183      │ │ KSh 1.5K │ │ 1,248    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├───────────────────────────────────┬─────────────────────┤
│  RECENT ORDERS                    │  TOP PRODUCTS       │
│  ┌─────────────────────────────┐  │  ┌────────────────┐ │
│  │ #10283  KSh 3,450  14:32   │  │  │ Coca Cola  52  │ │
│  │ #10282  KSh 1,200  14:28   │  │  │ Bread      41  │ │
│  │ #10281  KSh 890   14:15   │  │  │ Milk       38  │ │
│  └─────────────────────────────┘  │  └────────────────┘ │
└───────────────────────────────────┴─────────────────────┘
```

**API:** `GET /dashboard/` → `IDashboardStats`

---

### 2. Products (`/products`)

**Layout:** Table with search, filter by category, add/edit/delete.

```
┌─────────────────────────────────────────────────────────┐
│  Products                              [+ Add Product]   │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Search products...                Category: [▼] │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Name      │ Category │ Price    │ Stock │ Status │    │
│  │───────────┼──────────┼──────────┼───────│────────│    │
│  │ Coca Cola │ Drinks   │ KSh 120  │ 245   │ ●      │    │
│  │ Bread     │ Food     │ KSh 60   │ 12    │ ●      │    │
│  │ Milk 500ml│ Dairy    │ KSh 80   │ 0     │ ○      │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**API:** `GET /products/` → `IApiListResponse<IProduct>`

---

### 3. POS Terminal (`/pos`)

**Layout:** Split view — products grid (left), cart (right). Touch-optimized (min 48px tap targets).

```
┌──────────────────────────────────────────────────────────┐
│  JOAT STORES POS           Register #01        Joan [▼]  │
├─────────────────────────────────────┬────────────────────┤
│  🔍 Search products...              │  CART (3 items)    │
│                                     │                    │
│  ┌─────┐ ┌─────┐ ┌─────┐          │  Coca Cola    120  │
│  │     │ │     │ │     │          │  Bread         60  │
│  │Coca │ │Bread│ │Milk │          │  Milk         100  │
│  │Cola │ │     │ │     │          │                    │
│  │120  │ │60   │ │80   │          │  ────────────────  │
│  └─────┘ └─────┘ └─────┘          │  Subtotal      280 │
│                                     │  Tax (16%)      45 │
│  Categories                         │  ────────────────  │
│  [All] [Drinks] [Food] [Dairy]     │  TOTAL         325 │
│                                     │                    │
│  ┌─────┐ ┌─────┐ ┌─────┐          │  [CASH] [MPESA]   │
│  │Sugar│ │Water│ │Rice │          │  [CARD] [SPLIT]    │
│  │40   │ │30   │ │200  │          │                    │
│  └─────┘ └─────┘ └─────┘          │  [HOLD] [CLEAR]    │
└─────────────────────────────────────┴────────────────────┘
```

**Components:**
- `ProductGrid` — fetches products, renders touch-friendly cards
- `Cart` — shows items, quantity controls, totals, payment buttons
- `PaymentModal` — cash/mpesa/card payment flow
- `BarcodeScanner` — input field that searches by SKU/barcode

**API:**
- `GET /products/?search={query}` → product list
- `POST /cart/` → add item `{ variant_id, quantity }`
- `GET /cart/` → current cart
- `DELETE /cart/{item_id}/` → remove item
- `POST /checkout/` → `{ payment_method, customer_id?, notes }`

---

### 4. Waiter Dashboard (`/waiter`)

**Layout:** Mobile-first, simplified. Focus on taking orders and seeing today's stats.

```
┌──────────────────────┐
│  Waiter Dashboard    │
│  Welcome, Mwende     │
│  Shift: 08:00 - 16:00│
├──────────────────────┤
│  TODAY'S STATS       │
│  ┌────────┐┌────────┐│
│  │Orders  ││Revenue ││
│  │  23    ││ 12,450 ││
│  └────────┘└────────┘│
├──────────────────────┤
│  [+ NEW ORDER]       │
├──────────────────────┤
│  MY RECENT ORDERS    │
│  #10283  KSh 3,450   │
│  #10281  KSh 1,200   │
│  #10279  KSh 890     │
└──────────────────────┘
```

**API:**
- `GET /dashboard/` → stats filtered by waiter
- `POST /orders/` → create order with `served_by` field

---

### 5. Inventory (`/inventory`)

**Layout:** Table with stock levels, status badges, low stock alerts.

```
┌─────────────────────────────────────────────────────────┐
│  Inventory                                               │
│  Total Products: 1,248  Low Stock: 37  Out of Stock: 8  │
├─────────────────────────────────────────────────────────┤
│  Search products...               Filter: [All ▼]       │
├─────────────────────────────────────────────────────────┤
│  Product     │ SKU    │ Stock │ Status     │ Action      │
│  ────────────┼────────┼───────│────────────│─────────────│
│  Coca Cola   │ CC-001 │ 245   │ ● In Stock │ [Adjust]    │
│  Bread       │ BR-001 │ 12    │ ● Low      │ [Adjust]    │
│  Milk 500ml  │ ML-001 │ 0     │ ○ Out      │ [Adjust]    │
└─────────────────────────────────────────────────────────┘
```

**API:** `GET /inventory/` → `IInventoryItem[]`

---

### 6. Orders (`/orders`)

**Layout:** Transaction history with filters, status badges, receipt view.

```
┌─────────────────────────────────────────────────────────┐
│  Sales History                                           │
│  Today: KSh 284,500  |  183 transactions                │
├─────────────────────────────────────────────────────────┤
│  Date: [Today ▼]  Status: [All ▼]  Payment: [All ▼]    │
├─────────────────────────────────────────────────────────┤
│  Receipt   │ Time  │ Items │ Total   │ Payment │ Status │
│  ──────────┼───────┼───────│─────────│─────────│────────│
│  #10283    │ 14:32 │ 12    │ KSh 3.4K│ Cash    │ ●      │
│  #10282    │ 14:28 │ 3     │ KSh 1.2K│ M-Pesa  │ ●      │
│  #10281    │ 14:15 │ 1     │ KSh 890 │ Card    │ ●      │
└─────────────────────────────────────────────────────────┘
```

**API:** `GET /orders/` → `IApiListResponse<IOrder>`

---

### 7. Staff (`/staff`)

**Layout:** Staff list with role badges, invite/disable actions.

```
┌─────────────────────────────────────────────────────────┐
│  Staff                               [+ Add Staff]       │
├─────────────────────────────────────────────────────────┤
│  Name          │ Role      │ Status  │ Last Login       │
│  ──────────────│───────────│─────────│──────────────────│
│  Joan Kafuraha │ Owner     │ ● Active│ 2026-09-01 08:00 │
│  Mwende Kimani │ Cashier   │ ● Active│ 2026-09-01 09:15 │
│  Brian Otieno  │ Waiter    │ ● Active│ 2026-09-01 08:30 │
│  Sarah Wanjiku │ Manager   │ ○ Inactive│ —              │
└─────────────────────────────────────────────────────────┘
```

**API:** `GET /users/` → `IApiListResponse<IStaff>`

---

### 8. Platform Admin (`/platform`)

**Layout:** Platform-wide stats, store management, user management.

```
┌─────────────────────────────────────────────────────────┐
│  JOAT STORES — Platform Overview                         │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Stores   │ │ Users    │ │ Revenue  │ │GMV (MTD) │  │
│  │ 247      │ │ 1,832    │ │ KSh 128M │ │ KSh 12.4M│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├─────────────────────────────────────────────────────────┤
│  STORES                                                  │
│  Business          │ Stores │ Status   │ Plan            │
│  ──────────────────│────────│──────────│─────────────────│
│  Mama's Supermarket│ 4      │ ● Active │ Pro             │
│  Kibera Pharmacy   │ 2      │ ● Active │ Basic           │
│  ABC Hardware      │ 1      │ ○ Trial  │ Free            │
└─────────────────────────────────────────────────────────┘
```

**API:** `GET /platform/stores/` → store list

---

## Sidebar Navigation Update

Update `AdminSidebar.tsx` to include role-based nav:

```typescript
const STORE_NAV: NavItem[] = [
  { label: "Dashboard", href: "/dashboard/", icon: "Home" },
  { label: "POS Terminal", href: "/pos/", icon: "ShoppingCart" },
  { label: "Products", href: "/products/", icon: "Package" },
  { label: "Categories", href: "/categories/", icon: "Tags" },
  { label: "Inventory", href: "/inventory/", icon: "Box" },
  { label: "Orders", href: "/orders/", icon: "Receipt" },
  { label: "Customers", href: "/customers/", icon: "Users" },
  { label: "Staff", href: "/staff/", icon: "UserCog" },
  { label: "Reports", href: "/reports/", icon: "BarChart3" },
  { label: "Settings", href: "/settings/", icon: "Settings" },
];

const WAITER_NAV: NavItem[] = [
  { label: "Dashboard", href: "/waiter/", icon: "Home" },
  { label: "My Sales", href: "/waiter/my-sales/", icon: "BarChart3" },
];

const PLATFORM_NAV: NavItem[] = [
  { label: "Overview", href: "/platform/", icon: "LayoutDashboard" },
  { label: "Stores", href: "/platform/stores/", icon: "Store" },
  { label: "Users", href: "/platform/users/", icon: "Users" },
  { label: "Settings", href: "/platform/settings/", icon: "Settings" },
];
```

---

## TanStack Query Patterns

### API Hooks (`src/hooks/`)

Create `src/hooks/useProducts.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/query";
import { api } from "@/lib/api";
import type { IProduct, IApiListResponse } from "@/types";

// List products
export function useProducts(params?: { search?: string; category_id?: number }) {
  return useQuery({
    queryKey: ["products", params],
    queryFn: async () => {
      const { data } = await api.get<IApiListResponse<IProduct>>("/products/", { params });
      return data;
    },
  });
}

// Get single product
export function useProduct(id: number) {
  return useQuery({
    queryKey: ["product", id],
    queryFn: async () => {
      const { data } = await api.get<{ data: IProduct }>(`/products/${id}/`);
      return data.data;
    },
    enabled: !!id,
  });
}

// Create product
export function useCreateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (product: Partial<IProduct>) => {
      const { data } = await api.post<{ data: IProduct }>("/products/", product);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

// Update product
export function useUpdateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...product }: Partial<IProduct> & { id: number }) => {
      const { data } = await api.patch<{ data: IProduct }>(`/products/${id}/`, product);
      return data.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product", variables.id] });
    },
  });
}

// Delete product
export function useDeleteProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/products/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
```

Create `src/hooks/useDashboard.ts`:

```typescript
import { useQuery } from "@tanstack/query";
import { api } from "@/lib/api";
import type { IDashboardStats, ITopProduct } from "@/types";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => {
      const { data } = await api.get<{ data: IDashboardStats }>("/dashboard/");
      return data.data;
    },
    refetchInterval: 30000, // Refresh every 30s
  });
}
```

Create `src/hooks/useOrders.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/query";
import { api } from "@/lib/api";
import type { IOrder, IApiListResponse } from "@/types";

export function useOrders(params?: { status?: string; payment_method?: string }) {
  return useQuery({
    queryKey: ["orders", params],
    queryFn: async () => {
      const { data } = await api.get<IApiListResponse<IOrder>>("/orders/", { params });
      return data;
    },
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: ["order", id],
    queryFn: async () => {
      const { data } = await api.get<{ data: IOrder }>(`/orders/${id}/`);
      return data.data;
    },
    enabled: !!id,
  });
}
```

Create `src/hooks/useCart.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/query";
import { api } from "@/lib/api";
import type { ICartItem } from "@/types";

export function useCart() {
  return useQuery({
    queryKey: ["cart"],
    queryFn: async () => {
      const { data } = await api.get<{ data: ICartItem[] }>("/cart/");
      return data.data;
    },
  });
}

export function useAddToCart() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (item: { variant_id: number; quantity: number }) => {
      const { data } = await api.post<{ data: ICartItem }>("/cart/", item);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
    },
  });
}

export function useCheckout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      payment_method: "cash" | "mpesa" | "card";
      customer_id?: number;
      notes?: string;
    }) => {
      const { data } = await api.post<{ data: { order_id: string } }>("/checkout/", payload);
      return data.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
```

---

## Error Handling Pattern

### API Error Handler (`src/lib/api.ts` already has interceptor)

Use this pattern in all pages:

```typescript
import { useMutation } from "@tanstack/query";
import { useUIStore } from "@/stores/uiStore";

const addToast = useUIStore((s) => s.addToast);

const createProduct = useCreateProduct({
  onSuccess: () => {
    addToast({ type: "success", message: "Product created successfully" });
    router.push("/products/");
  },
  onError: (error: AxiosError<IApiErrorResponse>) => {
    const errors = error.response?.data?.errors;
    if (errors?.[0]) {
      addToast({ type: "error", message: errors[0].message });
    } else {
      addToast({ type: "error", message: "Something went wrong" });
    }
  },
});
```

### Validation Errors in Forms

```typescript
import { FieldErrors, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const productSchema = z.object({
  name: z.string().min(1, "Name is required"),
  category_id: z.number().nullable(),
  description: z.string().optional(),
});

type ProductFormData = z.infer<typeof productSchema>;

function ProductForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<ProductFormData>({
    resolver: zodResolver(productSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register("name")} />
      {errors.name && <p className="text-red-500 text-sm">{errors.name.message}</p>}
    </form>
  );
}
```

---

## Loading States

### Skeleton Loaders

```typescript
// Reusable skeleton components
export function StatCardSkeleton() {
  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="h-4 w-24 animate-pulse rounded bg-gray-200" />
      <div className="mt-2 h-8 w-32 animate-pulse rounded bg-gray-200" />
      <div className="mt-1 h-3 w-20 animate-pulse rounded bg-gray-200" />
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="rounded-lg border bg-white p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 py-3 border-b last:border-0">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="h-4 flex-1 animate-pulse rounded bg-gray-200" />
          ))}
        </div>
      ))}
    </div>
  );
}
```

### Page-Level Loading

```typescript
// In page component
export default function ProductsPage() {
  const { data: products, isLoading, error } = useProducts();

  if (isLoading) return <TableSkeleton rows={8} cols={5} />;

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-red-600">Failed to load products</p>
        <button onClick={() => window.location.reload()} className="mt-2 text-sm text-red-500 underline">
          Retry
        </button>
      </div>
    );
  }

  return ( /* render products */ );
}
```

---

## Component Code Examples

### StatCard Component (`src/components/ui/StatCard.tsx`)

```typescript
interface StatCardProps {
  label: string;
  value: string | number;
  change?: string;
  icon?: React.ReactNode;
}

export function StatCard({ label, value, change, icon }: StatCardProps) {
  return (
    <div className="rounded-lg border bg-white p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{label}</p>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
      {change && (
        <p className={`mt-1 text-xs ${change.startsWith("+") ? "text-green-600" : "text-red-600"}`}>
          {change}
        </p>
      )}
    </div>
  );
}
```

### DataTable Component (`src/components/ui/DataTable.tsx`)

```typescript
import { ReactNode } from "react";

interface Column<T> {
  header: string;
  accessor: keyof T | ((item: T) => ReactNode);
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
}

export function DataTable<T extends { id: string | number }>({
  columns,
  data,
  onRowClick,
  emptyMessage = "No data found",
}: DataTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="rounded-lg border bg-white p-12 text-center text-gray-500">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border bg-white">
      <table className="w-full">
        <thead className="border-b bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th key={String(col.header)} className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={item.id}
              onClick={() => onRowClick?.(item)}
              className={onRowClick ? "cursor-pointer hover:bg-gray-50" : ""}
            >
              {columns.map((col) => (
                <td key={String(col.header)} className="border-b px-4 py-3 text-sm text-gray-700">
                  {typeof col.accessor === "function"
                    ? col.accessor(item)
                    : String(item[col.accessor] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### Modal Component (`src/components/ui/Dialog.tsx`)

```typescript
"use client";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function Dialog({ open, onClose, title, children }: DialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    open ? dialog.showModal() : dialog.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="rounded-lg border bg-white p-0 shadow-xl backdrop:bg-black/50"
    >
      <div className="flex items-center justify-between border-b px-6 py-4">
        <h2 className="text-lg font-semibold">{title}</h2>
        <button onClick={onClose} className="rounded p-1 hover:bg-gray-100">
          <X size={20} />
        </button>
      </div>
      <div className="px-6 py-4">{children}</div>
    </dialog>
  );
}
```

### POS Product Card (`src/components/pos/ProductCard.tsx`)

```typescript
"use client";
import { formatCurrency } from "@/lib/utils";
import type { IProduct } from "@/types";

interface ProductCardProps {
  product: IProduct;
  onAdd: (variant_id: number, name: string, price: string) => void;
}

export function ProductCard({ product, onAdd }: ProductCardProps) {
  const defaultVariant = product.variants?.[0];
  if (!defaultVariant) return null;

  return (
    <button
      onClick={() => onAdd(defaultVariant.id, product.name, defaultVariant.price)}
      className="flex flex-col items-center rounded-lg border bg-white p-4 transition hover:border-blue-500 hover:shadow-md active:scale-95"
      style={{ minHeight: "48px" }}
    >
      {product.images?.[0] ? (
        <img src={product.images[0].image} alt={product.name} className="mb-2 h-16 w-16 rounded object-cover" />
      ) : (
        <div className="mb-2 flex h-16 w-16 items-center justify-center rounded bg-gray-100 text-2xl">
          {product.name[0]}
        </div>
      )}
      <span className="w-full truncate text-center text-sm font-medium">{product.name}</span>
      <span className="text-sm font-semibold text-blue-600">{formatCurrency(defaultVariant.price)}</span>
    </button>
  );
}
```

### POS Cart Item (`src/components/pos/CartItem.tsx`)

```typescript
"use client";
import { Minus, Plus, Trash2 } from "lucide-react";
import { formatCurrency } from "@/lib/utils";
import { useCartStore } from "@/stores/cartStore";
import type { ICartItem } from "@/types";

export function CartItem({ item }: { item: ICartItem }) {
  const { updateQuantity, removeItem } = useCartStore();

  return (
    <div className="flex items-center justify-between border-b py-3">
      <div className="flex-1">
        <p className="font-medium">{item.product_name}</p>
        <p className="text-sm text-gray-500">{formatCurrency(item.price)}</p>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => updateQuantity(item.variant_id, item.quantity - 1)}
          className="rounded p-1 hover:bg-gray-100"
          style={{ minHeight: "48px", minWidth: "48px" }}
        >
          <Minus size={16} />
        </button>
        <span className="w-8 text-center">{item.quantity}</span>
        <button
          onClick={() => updateQuantity(item.variant_id, item.quantity + 1)}
          className="rounded p-1 hover:bg-gray-100"
          style={{ minHeight: "48px", minWidth: "48px" }}
        >
          <Plus size={16} />
        </button>
        <button
          onClick={() => removeItem(item.variant_id)}
          className="rounded p-1 text-red-500 hover:bg-red-50"
          style={{ minHeight: "48px", minWidth: "48px" }}
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}
```

### Payment Modal (`src/components/pos/PaymentModal.tsx`)

```typescript
"use client";
import { useState } from "react";
import { useCartStore } from "@/stores/cartStore";
import { useCheckout } from "@/hooks/useCart";
import { formatCurrency } from "@/lib/utils";
import { Dialog } from "@/components/ui/Dialog";

interface PaymentModalProps {
  open: boolean;
  onClose: () => void;
}

export function PaymentModal({ open, onClose }: PaymentModalProps) {
  const { total, payment_method, setPaymentMethod, clearCart } = useCartStore();
  const checkout = useCheckout();
  const [cashReceived, setCashReceived] = useState("");

  const handlePayment = async () => {
    await checkout.mutateAsync({ payment_method });
    clearCart();
    onClose();
  };

  const change = payment_method === "cash"
    ? Math.max(0, parseFloat(cashReceived || "0") - parseFloat(total))
    : 0;

  return (
    <Dialog open={open} onClose={onClose} title="Complete Payment">
      <div className="space-y-4">
        <div className="text-center">
          <p className="text-sm text-gray-500">Total Due</p>
          <p className="text-3xl font-bold">{formatCurrency(total)}</p>
        </div>

        {/* Payment method selection */}
        <div className="grid grid-cols-3 gap-2">
          {(["cash", "mpesa", "card"] as const).map((method) => (
            <button
              key={method}
              onClick={() => setPaymentMethod(method)}
              className={`rounded-lg border-2 p-4 text-center font-medium transition ${
                payment_method === method
                  ? "border-blue-500 bg-blue-50 text-blue-700"
                  : "border-gray-200 hover:border-gray-300"
              }`}
              style={{ minHeight: "48px" }}
            >
              {method === "cash" ? "Cash" : method === "mpesa" ? "M-Pesa" : "Card"}
            </button>
          ))}
        </div>

        {/* Cash input */}
        {payment_method === "cash" && (
          <div>
            <label className="block text-sm font-medium text-gray-700">Cash Received</label>
            <input
              type="number"
              value={cashReceived}
              onChange={(e) => setCashReceived(e.target.value)}
              className="mt-1 block w-full rounded-lg border px-4 py-3 text-lg"
              placeholder="0.00"
              style={{ minHeight: "48px" }}
            />
            {change > 0 && (
              <p className="mt-1 text-sm text-green-600">Change: {formatCurrency(change)}</p>
            )}
          </div>
        )}

        <button
          onClick={handlePayment}
          disabled={checkout.isPending}
          className="w-full rounded-lg bg-blue-600 py-3 text-lg font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          style={{ minHeight: "48px" }}
        >
          {checkout.isPending ? "Processing..." : "Confirm Payment"}
        </button>
      </div>
    </Dialog>
  );
}
```

---

## Implementation Notes

1. **All API calls** go through `src/lib/api.ts` axios instance (handles auth headers + token refresh)
2. **Server Components by default** — only add `'use client'` for interactive islands (forms, modals, POS)
3. **TanStack Query** for all data fetching — query keys: `['products', params]`, `['orders', params]`
4. **Zustand** only for UI state (cart, modals, toasts) — not for server data
5. **Money** always as string in API, formatted with `formatCurrency()` in UI
6. **IDs** are integers (not UUIDs) — backend uses integer PKs
7. **No `localStorage`** for tokens — access token in Zustand memory, refresh token in httpOnly cookie
8. **Tailwind CSS** for all styling — no CSS modules, no styled-components
9. **Icons** use Lucide React (`lucide-react`) — already installed
10. **Touch targets** — all buttons/links min 48x48px for POS and Waiter views
11. **Responsive** — mobile-first for Waiter, tablet+ for POS, desktop for admin

---

## Build Order

1. **Day 1 Morning:** Types, utils, UI components (Button, Card, DataTable, Dialog, StatCard)
2. **Day 1 Afternoon:** Dashboard page + widgets + hooks
3. **Day 2 Morning:** Products + Categories pages + CRUD forms
4. **Day 2 Afternoon:** POS terminal (cart store, product grid, payment flow)
5. **Day 3 Morning:** Orders + Inventory pages
6. **Day 3 Afternoon:** Customers + Staff pages
7. **Day 4 Morning:** Waiter dashboard
8. **Day 4 Afternoon:** Platform admin pages, settings, final polish

---

*Generated: 2026-09-01 | Project: joat_stores | First Client: Bar + Restaurant*
