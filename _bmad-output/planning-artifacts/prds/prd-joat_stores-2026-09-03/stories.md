---
project: joat_stores
status: draft
created: 2026-09-03
epicsCount: 8
storiesCount: 38
---

# Epics & Stories — JOAT Stores: Store Owner Functionality & User Roles

## Priority Matrix

| Priority | Epics | Rationale |
|----------|-------|-----------|
| **P0 (Launch)** | Product Management, POS & Sales | Can't run a bar without products and payments |
| **P1 (Week 2)** | Pricing & Offers, Store Settings | Revenue protection + legal compliance |
| **P2 (Month 2)** | Inventory, Staff Management | Profit protection + security |
| **P3 (v2)** | Reports & Analytics, Customer Features | Retention + intelligence |

---

## Epic 1: Product Management (P0 — Launch)

**Goal:** Store owner can create, edit, and manage products with prices and categories.

### Story 1.1: Product Table with Inline Edit
**As a** store owner
**I want to** see all products in a table with inline editing
**So that** I can quickly add and update products

**Acceptance Criteria:**
- [ ] Product table shows: name, price (first variant), category, stock, status
- [ ] Click on any cell to edit inline (name, price, category)
- [ ] "Add Product" row at bottom of table (like Airtable)
- [ ] Save on blur or Enter key
- [ ] Delete button with confirmation dialog
- [ ] Search and category filter work

**Technical Notes:**
- Backend: `ProductViewSet` already supports CRUD
- Frontend: New component `ProductTable` with inline editing
- Wire `check_product_limit` into `ProductViewSet.create()`

---

### Story 1.2: CSV Product Import
**As a** store owner
**I want to** import products from a CSV file
**So that** I can bulk-add my menu without manual entry

**Acceptance Criteria:**
- [ ] "Import CSV" button on products page
- [ ] Download template CSV with column headers
- [ ] Drag-and-drop upload zone
- [ ] Column mapping preview (auto-detect name, price, category, stock)
- [ ] Validation errors shown per row
- [ ] Bulk create on confirmation

**Technical Notes:**
- Backend: New endpoint `POST /api/v1/store/products/import/`
- Use `csv` module for parsing, `bulk_create` for performance
- Return created count + error details

---

### Story 1.3: Variant Management
**As a** store owner
**I want to** add size variants to products (pint, bottle, pitcher)
**So that** I can sell the same drink in different sizes

**Acceptance Criteria:**
- [ ] "Add Size" button on product row appends variant row
- [ ] Variant rows show: size name, price, SKU, stock
- [ ] Inline edit for variant price and stock
- [ ] Delete variant with confirmation
- [ ] At least one variant required per product

**Technical Notes:**
- Backend: `VariantViewSet` already supports CRUD
- Frontend: Nested rows under product in table

---

### Story 1.4: Category Management
**As a** store owner
**I want to** create and manage product categories
**So that** my menu is organized

**Acceptance Criteria:**
- [ ] Category list page with create/edit/delete
- [ ] Categories can have subcategories (hierarchy)
- [ ] Products filterable by category in POS
- [ ] Default categories seeded: Beers, Spirits, Cocktails, Food

**Technical Notes:**
- Backend: `CategoryViewSet` already supports CRUD
- Frontend: Already exists at `/categories/`

---

### Story 1.5: Product Availability Toggle
**As a** store owner
**I want to** toggle product availability (in stock/out of stock)
**So that** unavailable items don't appear in POS

**Acceptance Criteria:**
- [ ] Toggle switch on product table row
- [ ] Unavailable products hidden from POS product grid
- [ ] Toggle updates instantly (optimistic UI)
- [ ] Status shown as badge (green=available, red=unavailable)

**Technical Notes:**
- Backend: `Product.is_available` field already exists
- Frontend: Add toggle component to product table

---

## Epic 2: Pricing & Offers (P1 — Week 2)

**Goal:** Store owner can set prices, create discounts, and run promotions.

### Story 2.1: Price Management
**As a** store owner
**I want to** set and update product prices
**So that** I can price my products correctly

**Acceptance Criteria:**
- [ ] Price editable inline on product table
- [ ] Price changes reflected immediately in POS
- [ ] Price must be > 0
- [ ] Price displayed in KES format

**Technical Notes:**
- Backend: `Variant.price` field already exists
- Frontend: Inline edit on product table

---

### Story 2.2: Percentage Discounts
**As a** store owner
**I want to** create percentage-off discounts on products
**So that** I can run promotions

**Acceptance Criteria:**
- [ ] "Discount" column on product table
- [ ] Set discount percentage (0-90%)
- [ ] Discount applied at checkout
- [ ] Original price shown with strikethrough
- [ ] Discount auto-expires if set

**Technical Notes:**
- Backend: Add `discount_percent` and `discount_expires_at` to Variant
- Frontend: Show discount badge on product

---

### Story 2.3: Fixed Amount Discounts
**As a** store owner
**I want to** create fixed amount (KES) discounts
**So that** I can offer specific savings

**Acceptance Criteria:**
- [ ] Set discount amount in KES
- [ ] Discount cannot exceed product price
- [ ] Discount applied at checkout
- [ ] Savings displayed to customer

**Technical Notes:**
- Backend: Add `discount_amount` field (alternative to percentage)
- Validation: `discount_amount < variant.price`

---

### Story 2.4: Promo Codes
**As a** store owner
**I want to** create promo codes with conditions
**So that** I can run targeted promotions

**Acceptance Criteria:**
- [ ] Create promo code with: code, discount type, value, min order, expiry, usage limit
- [ ] Code validated at checkout
- [ ] Usage tracked per code
- [ ] Expired/used codes rejected

**Technical Notes:**
- Backend: New `PromoCode` model (TenantModel)
- Fields: code, discount_type, discount_value, min_order_amount, expires_at, usage_limit, usage_count, is_active

---

### Story 2.5: Daily Specials
**As a** store owner
**I want to** schedule recurring daily discounts
**So that** I can run "Ladies Night" or "Taco Tuesday" promos

**Acceptance Criteria:**
- [ ] Create daily special with: name, discount, days of week, time window
- [ ] Special activates automatically on scheduled days
- [ ] Special deactivates outside time window
- [ ] Multiple specials can run on same day

**Technical Notes:**
- Backend: New `DailySpecial` model (TenantModel)
- Fields: name, discount_percent, days_of_week (JSON), start_time, end_time, is_active
- Similar to existing `HappyHour` model but for retail products

---

### Story 2.6: Bundle Discounts
**As a** store owner
**I want to** create "buy X get Y free" deals
**So that** I can encourage volume purchases

**Acceptance Criteria:**
- [ ] Create bundle: buy_quantity, get_quantity, applies_to_product
- [ ] Bundle applied automatically at checkout
- [ ] Multiple bundles can stack
- [ ] Bundle usage tracked

**Technical Notes:**
- Backend: New `BundleOffer` model (TenantModel)
- Fields: buy_quantity, get_quantity, applies_to FK, is_active

---

## Epic 3: POS & Sales (P0 — Launch)

**Goal:** Complete POS flow with tax, receipts, and returns.

### Story 3.1: Tax Configuration
**As a** store owner
**I want to** set tax rate for my store
**So that** I comply with KRA regulations

**Acceptance Criteria:**
- [ ] Tax rate setting in store settings (default 16%)
- [ ] Tax-inclusive pricing option (default: yes, Kenya standard)
- [ ] Tax breakdown shown on receipts
- [ ] Tax calculated correctly in checkout

**Technical Notes:**
- Backend: Add `tax_rate` and `tax_inclusive` to `StoreSettings`
- Frontend: Add tax settings to settings page
- Checkout: Extract/add tax based on setting

---

### Story 3.2: Receipt Generation
**As a** store owner/staff
**I want to** generate receipts after sales
**So that** customers have proof of purchase

**Acceptance Criteria:**
- [ ] Receipt generated after each sale
- [ ] Receipt shows: store name/logo, items, quantities, prices, tax, total, payment method, M-Pesa receipt number
- [ ] Receipt can be printed or shared
- [ ] Receipt stored for reference

**Technical Notes:**
- Backend: New endpoint `GET /api/v1/store/orders/{id}/receipt/`
- Return structured JSON for POS printing
- Frontend: Receipt component with print button

---

### Story 3.3: Return/Refund Processing
**As a** store owner
**I want to** process returns and refunds
**So that** I can handle customer complaints

**Acceptance Criteria:**
- [ ] Return button on order detail page
- [ ] Owner approval required for refunds > KES 0
- [ ] Refund logged with: order_id, amount, reason, processed_by, timestamp
- [ ] Inventory restored on return
- [ ] Payment reversed (M-Pesa or cash)

**Technical Notes:**
- Backend: Extend `ReversePaymentView` with approval workflow
- New model: `RefundLog` (immutable audit trail)
- Permission: `store_owner` only for approval

---

### Story 3.4: Hold Order
**As a** cashier
**I want to** hold an order and recall it later
**So that** I can handle multiple customers simultaneously

**Acceptance Criteria:**
- [ ] "Hold" button on POS saves current cart
- [ ] Held orders shown in sidebar
- [ ] Click to recall held order
- [ ] Multiple orders can be held
- [ ] Held orders persist for 24 hours

**Technical Notes:**
- Frontend: Store held orders in localStorage
- Backend: No changes needed (cart is Redis-based)

---

### Story 3.5: Quick Keys / Favorites
**As a** cashier
**I want to** set up quick-access product buttons
**So that** I can ring up popular items fast

**Acceptance Criteria:**
- [ ] Favorites bar at top of POS
- [ ] Add product to favorites with star icon
- [ ] One-click add to cart from favorites
- [ ] Favorites persist per user

**Technical Notes:**
- Backend: New field `User.favorite_products` (JSON list)
- Frontend: Favorites bar component

---

## Epic 4: Inventory (P2 — Month 2)

**Goal:** Track stock levels, adjustments, and history.

### Story 4.1: Stock Adjustment
**As a** store owner
**I want to** manually adjust stock counts
**So that** I can correct inventory discrepancies

**Acceptance Criteria:**
- [ ] "Adjust" button on inventory page per variant
- [ ] Adjustment form: quantity change (positive/negative), reason (dropdown), notes
- [ ] Adjustment logged with: variant, delta, reason, user, timestamp
- [ ] Stock count updated atomically

**Technical Notes:**
- Backend: New `StockAdjustment` model (TenantModel)
- Fields: variant FK, delta (signed integer), reason (choices), user FK, created_at
- Endpoint: `POST /api/v1/store/inventory/adjust/`

---

### Story 4.2: Stock Count / Stocktake
**As a** store owner
**I want to** perform periodic stock counts
**So that** I can verify actual vs system stock

**Acceptance Criteria:**
- [ ] "Start Count" button creates stocktake session
- [ ] List all variants with system qty and input for counted qty
- [ ] Variance auto-calculated
- [ ] Commit stocktake creates adjustment records for differences
- [ ] Stocktake history with date, counted_by, variance summary

**Technical Notes:**
- Backend: New `StockCount` + `StockCountLine` models
- Endpoint: `POST /api/v1/store/inventory/counts/` (start), `POST .../commit/` (commit)
- Use `select_for_update` to prevent concurrent counts

---

### Story 4.3: Stock Movement History
**As a** store owner
**I want to** view stock movement history per product
**So that** I can track what happened to my inventory

**Acceptance Criteria:**
- [ ] History list per variant showing: date, type (sale/restock/adjustment/count), quantity change, user
- [ ] Filter by date range and type
- [ ] Export to CSV

**Technical Notes:**
- Backend: `GET /api/v1/store/inventory/adjustments/?variant={id}`
- Read-only view of `StockAdjustment` records

---

### Story 4.4: Low-Stock Alerts
**As a** store owner
**I want to** receive alerts when stock is low
**So that** I can reorder before running out

**Acceptance Criteria:**
- [ ] Low-stock threshold per product (default: 5)
- [ ] WhatsApp notification when stock falls below threshold
- [ ] Alert queued in `inventory.alerts` Celery queue
- [ ] Alert includes product name and current stock

**Technical Notes:**
- Backend: Extend `Variant.save()` to fire alert on adjustment
- Celery task: `send_low_stock_alert` on `inventory.alerts` queue

---

### Story 4.5: Reorder Suggestions
**As a** store owner
**I want to** see which products need reorder
**So that** I can maintain adequate stock

**Acceptance Criteria:**
- [ ] Report shows products below reorder point
- [ ] Suggested reorder quantity based on sales velocity
- [ ] One-click "Mark as Ordered" button

**Technical Notes:**
- Backend: New endpoint `GET /api/v1/store/inventory/reorder/`
- Calculation: `reorder_qty = avg_daily_sales * lead_time_days - current_stock`

---

## Epic 5: Staff Management (P2 — Month 2)

**Goal:** Manage staff with proper roles and permissions.

### Story 5.1: Staff Edit/Deactivate
**As a** store owner
**I want to** edit staff details and deactivate accounts
**So that** I can manage my team

**Acceptance Criteria:**
- [ ] Edit button on staff list page
- [ ] Edit form: name, email, role, status
- [ ] Deactivate button prevents login
- [ ] Deactivated staff shown as "Inactive"

**Technical Notes:**
- Backend: `UserDetailView` already supports PATCH/DELETE
- Frontend: Add edit/deactivate buttons to staff page

---

### Story 5.2: Role-Based Permissions
**As a** store owner
**I want to** assign roles with different access levels
**So that** staff only access what they need

**Acceptance Criteria:**
- [ ] 5 roles: owner, manager, cashier, waiter, kitchen
- [ ] Permission matrix enforced at backend
- [ ] Cashier: POS only
- [ ] Waiter: tabs + orders only
- [ ] Kitchen: view orders only

**Technical Notes:**
- Backend: Add `cashier`, `waiter`, `kitchen` to `User.Role` enum
- New `HasPermission` DRF class with permission matrix
- Replace `IsStoreManager` on sensitive views

---

### Story 5.3: Staff Activity Log
**As a** store owner
**I want to** view staff activity
**So that** I can monitor performance and detect issues

**Acceptance Criteria:**
- [ ] Activity log per staff member
- [ ] Shows: timestamp, action, resource, details
- [ ] Filter by date range and action type
- [ ] Export to CSV

**Technical Notes:**
- Backend: New `StaffActivityLog` model (immutable)
- Fields: user FK, action, resource_type, resource_id, details JSON, timestamp

---

### Story 5.4: PIN Login for Staff
**As a** cashier/waiter
**I want to** log in with PIN instead of email/password
**So that** I can access the system quickly

**Acceptance Criteria:**
- [ ] PIN entry screen on POS
- [ ] 4-6 digit PIN
- [ ] Session tied to PIN user
- [ ] Activity logged against PIN user

**Technical Notes:**
- Backend: New endpoint `POST /api/v1/auth/staff-pin/`
- Validate PIN against stored hash
- Issue JWT with staff role

---

## Epic 6: Store Settings (P1 — Week 2)

**Goal:** Configure store profile, branding, and payment methods.

### Story 6.1: Store Profile Editor
**As a** store owner
**I want to** edit my store profile
**So that** my store information is correct

**Acceptance Criteria:**
- [ ] Settings page with form fields: name, description, contact, currency, timezone
- [ ] Save button persists changes
- [ ] Changes reflected in storefront

**Technical Notes:**
- Backend: New `StoreSettingsView` with GET/PATCH
- Frontend: Replace stub settings page with form

---

### Story 6.2: Logo Upload
**As a** store owner
**I want to** upload my store logo
**So that** my brand is visible

**Acceptance Criteria:**
- [ ] Logo upload on settings page
- [ ] Accepted formats: jpg, png, webp, max 5MB
- [ ] Logo displays in admin header and storefront
- [ ] Logo included in onboarding email

**Technical Notes:**
- Backend: `StoreSettings.logo_url` field already exists
- Frontend: File upload component

---

### Story 6.3: Theme/Branding Editor
**As a** store owner
**I want to** customize my store's look and feel
**So that** it matches my brand

**Acceptance Criteria:**
- [ ] Theme editor with color pickers
- [ ] Live preview of changes
- [ ] Preset themes to choose from
- [ ] Save applies to storefront

**Technical Notes:**
- Backend: `ThemeDetailView` already supports CRUD
- Frontend: New theme editor page

---

### Story 6.4: Payment Method Configuration
**As a** store owner
**I want to** enable/disable payment methods
**So that** I control how customers pay

**Acceptance Criteria:**
- [ ] Toggle switches for: M-Pesa, Cash, Card
- [ ] At least one method must be enabled
- [ ] Disabled methods hidden from POS and checkout
- [ ] M-Pesa configuration: till number, business name

**Technical Notes:**
- Backend: New `PaymentMethodConfig` model
- Fields: provider, enabled, config_json, display_order

---

### Story 6.5: Notification Configuration
**As a** store owner
**I want to** configure which notifications I receive
**So that** I'm not overwhelmed

**Acceptance Criteria:**
- [ ] Notification preferences: order updates, low stock, daily summary
- [ ] Channel preferences: email, WhatsApp, both
- [ ] Quiet hours setting (no notifications during off-hours)

**Technical Notes:**
- Backend: Extend `StoreSettings` with notification preferences
- Frontend: Notification settings section

---

## Epic 7: Reports & Analytics (P3 — v2)

**Goal:** Sales reports, inventory reports, staff performance.

### Story 7.1: Sales Reports
**As a** store owner
**I want to** view sales reports
**So that** I understand my business performance

**Acceptance Criteria:**
- [ ] Daily/weekly/monthly sales summary
- [ ] Revenue, order count, average order value
- [ ] Top products by revenue and quantity
- [ ] Export to CSV

**Technical Notes:**
- Backend: Read from `DailyRevenueSummary` model
- Endpoint: `GET /api/v1/store/reports/sales/`

---

### Story 7.2: Inventory Reports
**As a** store owner
**I want to** view inventory reports
**So that** I can manage stock effectively

**Acceptance Criteria:**
- [ ] Current stock levels with valuation
- [ ] Stock movement history
- [ ] Low-stock alerts list
- [ ] Export to CSV

**Technical Notes:**
- Backend: Read from `StockAdjustment` model
- Endpoint: `GET /api/v1/store/reports/inventory/`

---

### Story 7.3: Staff Performance Reports
**As a** store owner
**I want to** view staff performance
**So that** I can recognize top performers

**Acceptance Criteria:**
- [ ] Orders processed per staff member
- [ ] Revenue per staff member
- [ ] Time period filter (daily/weekly/monthly)
- [ ] Export to CSV

**Technical Notes:**
- Backend: Read from `StaffActivityLog` model
- Endpoint: `GET /api/v1/store/reports/staff/`

---

### Story 7.4: Customer Insights
**As a** store owner
**I want to** view customer purchase patterns
**So that** I can understand my customer base

**Acceptance Criteria:**
- [ ] Top customers by revenue
- [ ] Repeat customer rate
- [ ] Loyalty points redeemed
- [ ] Export to CSV

**Technical Notes:**
- Backend: Read from `CustomerProfile` and `LoyaltyAccount` models
- Endpoint: `GET /api/v1/store/reports/customers/`

---

## Epic 8: Customer Features (P3 — v2)

**Goal:** Customer accounts, loyalty, WhatsApp summaries.

### Story 8.1: Customer Accounts
**As a** customer
**I want to** create an account and view my order history
**So that** I can track my purchases

**Acceptance Criteria:**
- [ ] Registration with email/phone
- [ ] Order history page
- [ ] Loyalty points balance
- [ ] Profile editing

**Technical Notes:**
- Backend: `CustomerProfile` model already exists
- Frontend: Customer portal page

---

### Story 8.2: Loyalty Program Management
**As a** store owner
**I want to** configure loyalty rules
**So that** I can reward repeat customers

**Acceptance Criteria:**
- [ ] Points per KES spent (configurable)
- [ redemption rate (e.g., 100 points = KES 10)
- [ ] Expiry policy (e.g., points expire after 12 months)
- [ ] Loyalty dashboard showing points earned/redeemed

**Technical Notes:**
- Backend: `LoyaltyAccount` and `PointsTransaction` models already exist
- Frontend: Loyalty settings page

---

### Story 8.3: WhatsApp Daily Summary
**As a** store owner
**I want to** receive daily summary via WhatsApp
**So that** I stay informed without checking the dashboard

**Acceptance Criteria:**
- [ ] Daily summary sent at 10pm EAT
- [ ] Includes: revenue, order count, top 3 items, vs yesterday
- [ ] Sent via Twilio WhatsApp API
- [ ] Failed sends retried (max 3 attempts)

**Technical Notes:**
- Backend: Celery Beat task at 22:00 EAT
- Use `send_whatsapp_notification` task (already exists, needs wiring)

---

## User Role Stories

### Platform Admin Stories

**PA-1: Store Provisioning**
- Create store with name, domain, type, owner email, logo
- Generate temporary password, send onboarding email
- See onboarding success dialog with credentials

**PA-2: Platform Metrics**
- View 12 KPI cards: stores, subscriptions, revenue, orders, health
- Stores table with status management (activate/suspend)
- Plan distribution and recent signups

**PA-3: Subscription Management**
- Create/edit plans with pricing and features
- View all subscriptions with status
- Suspend stores after grace period

**PA-4: User Management**
- List all users across stores
- View user details and store assignments
- Deactivate user accounts

### Store Owner Stories

**SO-1: Full Store Management**
- All product, category, variant CRUD
- All order management (view, confirm, cancel)
- All staff management (create, edit, deactivate)
- All settings management (profile, theme, payments)
- All reports access

**SO-2: Financial Operations**
- Process refunds (with audit trail)
- View payment history
- Configure tax rates
- Export financial reports

**SO-3: Promotions Management**
- Create/edit/delete discounts
- Create/edit/delete promo codes
- Create/edit/delete daily specials
- View promotion performance

### Store Manager Stories

**SM-1: Operational Access**
- View products (read-only)
- Manage orders (confirm, fulfill)
- Process payments
- View reports (daily summaries)
- Manage happy hours

**SM-2: Inventory Operations**
- Adjust stock (with audit trail)
- Perform stock counts
- View inventory reports

### Cashier Stories

**CS-1: POS Operations**
- Process sales (cash/M-Pesa/card)
- Hold and recall orders
- View order history
- Print receipts

**CS-2: Payment Processing**
- Process payments on settled tabs
- Request refunds (owner approval required)
- View payment history

### Waiter Stories

**WT-1: Tab Management**
- Open tabs for walk-in customers
- Add rounds to tabs
- Request bills
- View today's orders

**WT-2: Sales Tracking**
- View personal sales for the shift
- See orders processed
- See revenue generated

### Kitchen Stories

**KT-1: Order Management**
- View pending orders
- Mark items as prepared
- View order details

**KT-2: Kitchen Display**
- See order queue
- Update order status
- View preparation times

---

## RBAC Permission Matrix

| Resource | owner | manager | cashier | waiter | kitchen |
|----------|:-----:|:-------:|:-------:|:------:|:-------:|
| Products | CRUD | Read | Read | Read | Read |
| Orders | Full | Full | Read | Create | Read |
| Payments | Full | Full | Process | None | None |
| Refunds | Approve | Request | Request | None | None |
| Inventory | Full | Adjust | None | None | None |
| Staff | Full | None | None | None | None |
| Settings | Full | Read | None | None | None |
| Reports | Full | Daily | None | None | None |
| Happy Hours | CRUD | CRUD | Read | Read | None |
| Tabs | Full | Full | Close | Open+Add | Read |

---

## Implementation Priority

### 2-Week MVP (P0)
1. Product table with inline edit (Story 1.1)
2. CSV import (Story 1.2)
3. Tax configuration (Story 3.1)
4. Store profile editor (Story 6.1)
5. Logo upload (Story 6.2)

### Week 3-4 (P1)
6. Variant management (Story 1.3)
7. Price management (Story 2.1)
8. Percentage discounts (Story 2.2)
9. Receipt generation (Story 3.2)
10. Payment method config (Story 6.4)

### Month 2 (P2)
11. Stock adjustment (Story 4.1)
12. Stock count (Story 4.2)
13. Staff edit/deactivate (Story 5.1)
14. Role-based permissions (Story 5.2)
15. Returns/refunds (Story 3.3)

### v2 (P3)
16. Promo codes (Story 2.4)
17. Daily specials (Story 2.5)
18. Bundle discounts (Story 2.6)
19. Sales reports (Story 7.1)
20. WhatsApp daily summary (Story 8.3)
