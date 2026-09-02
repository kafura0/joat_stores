# JOAT Stores — Data Model Reference

## Base Classes

### TenantModel (core.models)

All tenant-scoped domain models inherit from `TenantModel`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key, auto-generated |
| `store` | ForeignKey(Store) | Tenant FK, CASCADE, indexed |

Provides:
- `TenantQuerySet` manager with `.for_store(store)` filtering
- Soft delete via `django-safedelete` (SOFT_DELETE_CASCADE)

### SoftDeleteModel (core.models)

Used by `Store` itself (the tenant root).

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUIDField | Primary key |

---

## Store Module

### Store

**Inherits:** SafeDeleteModel (NOT TenantModel — it IS the tenant root)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUIDField | PK | Tenant identifier |
| `name` | CharField(255) | | Store display name |
| `slug` | SlugField(100) | unique | URL-friendly identifier |
| `domain` | CharField(253) | unique, indexed | FQDN for Nginx routing |
| `tenant_type` | CharField(20) | choices: retail/restaurant/bar/contracting | Business vertical |
| `status` | CharField(20) | choices: pending/active/suspended/cancelled | Lifecycle state |
| `currency` | CharField(3) | default: "KES" | ISO 4217 currency code |
| `payment_methods` | ArrayField | default: [] | Enabled payment methods |
| `country` | CharField(2) | default: "KE" | ISO 3166-1 alpha-2 |
| `timezone` | CharField(63) | default: "Africa/Nairobi" | IANA timezone |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last update timestamp |

**Custom Logic:**
- `save()` enforces `tenant_type` immutability once orders exist
- `_has_existing_orders()` checks across DineInOrder and Order models

### StoreSettings

**Inherits:** TenantModel

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tagline` | CharField(255) | "" | Store tagline |
| `logo_url` | URLField | "" | Store logo URL |
| `low_stock_threshold` | IntegerField | 5 | Low-stock alert threshold |

### StoreTheme

**Inherits:** TenantModel

45 fields covering design tokens:
- Preset slug + template style
- 14 colour palette fields
- 4 typography fields
- 3 spacing fields
- 4 border radius fields
- 3 shadow fields
- Announcement bar settings
- Custom CSS field

---

## Product Module

### Category

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(100) | Category name |
| `description` | TextField | Optional description |
| `position` | IntegerField | Sort order |
| `parent` | ForeignKey(self) | Parent category (hierarchical) |

### Product

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(255) | Product name |
| `description` | TextField | Product description |
| `attribute_names` | JSONField | e.g. ["Size", "Colour"] |
| `is_available` | BooleanField | Availability flag |
| `category` | ForeignKey(Category) | Parent category |

### Variant

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `attribute_values` | JSONField | e.g. {"Size": "M", "Colour": "Red"} |
| `price` | DecimalField(10,2) | Unit price |
| `inventory_count` | IntegerField | Stock quantity |
| `is_available` | BooleanField | Availability flag |
| `sku` | CharField(100) | Stock keeping unit |
| `product` | ForeignKey(Product) | Parent product |

**Custom Logic:**
- `save()` dispatches low-stock alert via `transaction.on_commit` when `inventory_count <= threshold`

### ProductImage

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `image` | ImageField | Uploaded image (WebP ≤ 800KB) |
| `alt_text` | CharField(255) | Alt text for accessibility |
| `position` | IntegerField | Sort order |
| `is_default` | BooleanField | Primary image flag |
| `product` | ForeignKey(Product) | Parent product |
| `variant` | ForeignKey(Variant) | Optional variant link |

---

## Order Module

### Order

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `customer_phone` | CharField(30) | Customer phone (E.164) |
| `customer_name` | CharField(255) | Customer name |
| `customer_email` | EmailField | Customer email |
| `delivery_address` | JSONField | Delivery address (nullable) |
| `items_snapshot` | JSONField | Denormalized line items |
| `total_amount` | DecimalField(10,2) | Order total |
| `status` | CharField(20) | pending/confirmed/fulfilled/completed/cancelled |
| `confirmed_at` | DateTimeField | Confirmation timestamp |
| `fulfilled_at` | DateTimeField | Fulfillment timestamp |
| `completed_at` | DateTimeField | Completion timestamp |
| `cancelled_at` | DateTimeField | Cancellation timestamp |
| `created_at` | DateTimeField | Creation timestamp |
| `payment_transaction` | ForeignKey(MpesaTransaction) | Linked payment |
| `customer` | ForeignKey(User) | Registered customer (nullable) |

**State Machine:**
```
PENDING → CONFIRMED → FULFILLED → COMPLETED
PENDING → CANCELLED
CONFIRMED → CANCELLED (with reversal)
```

### CartSnapshot

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `cart_key` | CharField(255) | Session key or user ID |
| `items` | JSONField | Cart items |
| `created_at` | DateTimeField | Creation timestamp |
| `linked_order` | OneToOneField(Order) | Linked order after checkout |

---

## Payment Module

### MpesaTransaction

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `reference` | CharField(100) | indexed | Payment reference |
| `phone` | CharField(20) | | Payer phone |
| `amount` | DecimalField(10,2) | | Payment amount |
| `status` | CharField(30) | | STK_PUSH_INITIATED/CONFIRMED/EXPIRED/FAILED/REVERSED |
| `checkout_request_id` | CharField(100) | | Daraja checkout ID |
| `mpesa_receipt_number` | CharField(50) | unique | M-Pesa receipt |
| `merchant_request_id` | CharField(100) | | Daraja merchant ID |
| `initiated_at` | DateTimeField | | Initiation timestamp |
| `completed_at` | DateTimeField | | Completion timestamp |
| `reversal_reason` | CharField(255) | | Reversal reason |

### CardTransaction

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `reference` | CharField(100) | Payment reference |
| `amount` | DecimalField(10,2) | Payment amount |
| `currency` | CharField(3) | Currency code |
| `status` | CharField(30) | PI_CREATED/PROCESSING/SUCCEEDED/FAILED/REFUNDED |
| `stripe_payment_intent_id` | CharField(255) | Stripe ID |
| `stripe_client_secret` | TextField | Client secret for frontend |
| `provider` | CharField(20) | stripe or flutterwave |
| `customer_email` | EmailField | Customer email |
| `initiated_at` | DateTimeField | Initiation timestamp |
| `completed_at` | DateTimeField | Completion timestamp |
| `failure_reason` | TextField | Failure reason |

---

## Restaurant Module

### MenuSection

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | CharField(100) | | Section name |
| `description` | TextField | | Section description |
| `position` | PositiveSmallIntegerField | indexed | Sort order |

**Constraints:** UniqueConstraint(store, name)

### MenuItem

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(150) | Item name |
| `description` | TextField | Item description |
| `price` | DecimalField(10,2) | Base price |
| `contains_allergens` | BooleanField | Allergen flag |
| `allergen_description` | TextField | Allergen details |
| `is_age_restricted` | BooleanField | 18+ flag |
| `is_available` | BooleanField | Availability flag |
| `available_from` | TimeField | Availability window start |
| `available_until` | TimeField | Availability window end |
| `position` | PositiveSmallIntegerField | Sort order |
| `section` | ForeignKey(MenuSection) | Parent section |

**Custom Logic:**
- `is_available_now(current_time)` checks time-based availability

### ModifierGroup

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(100) | Group name |
| `min_selections` | PositiveSmallIntegerField | Minimum selections |
| `max_selections` | PositiveSmallIntegerField | Maximum selections |
| `is_required` | BooleanField | Required flag |
| `menu_item` | ForeignKey(MenuItem) | Parent item |

### Modifier

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(100) | Modifier name |
| `price_addition` | DecimalField(10,2) | Price add-on |
| `is_available` | BooleanField | Availability flag |
| `modifier_group` | ForeignKey(ModifierGroup) | Parent group |

### Table

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `number` | PositiveSmallIntegerField | | Table number |
| `name` | CharField(50) | | Friendly name |
| `capacity` | PositiveSmallIntegerField | default: 2 | Seating capacity |
| `is_active` | BooleanField | | Active flag |

**Constraints:** UniqueConstraint(store, number)

### TableSession

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `status` | CharField(20) | OPEN/BILL_REQUESTED/CLOSED |
| `opened_at` | DateTimeField | Opening timestamp |
| `closed_at` | DateTimeField | Closing timestamp |
| `table` | ForeignKey(Table) | Parent table |
| `assigned_waiter` | ForeignKey(User) | Assigned waiter |

**Constraints:** UniqueConstraint(table, status) WHERE status='open'

**State Machine:**
```
OPEN → BILL_REQUESTED → CLOSED
```

### DineInOrder

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `status` | CharField(20) | PENDING/CONFIRMED/READY/CANCELLED |
| `items_snapshot` | JSONField | Denormalized items |
| `total_amount` | DecimalField(10,2) | Order total |
| `order_type` | CharField(20) | dine_in/takeaway |
| `pickup_reference` | CharField(20) | Takeaway reference |
| `placed_at` | DateTimeField | Order timestamp |
| `session` | ForeignKey(TableSession) | Parent session (nullable for takeaway) |
| `payment_transaction` | ForeignKey(MpesaTransaction) | Linked payment |

### KitchenTicket

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `status` | CharField(20) | PENDING/IN_PROGRESS/COMPLETED/CANCELLED |
| `items_snapshot` | JSONField | Copy of DineInOrder items |
| `waiter_name` | CharField(200) | Denormalized waiter name |
| `table_number` | PositiveSmallIntegerField | Denormalized table number |
| `created_at` | DateTimeField | Creation timestamp |
| `order` | OneToOneField(DineInOrder) | Parent order |

**State Machine:**
```
PENDING → IN_PROGRESS → COMPLETED/CANCELLED
```

### PendingOrder

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `phone` | CharField(20) | Customer phone (E.164) |
| `pin` | CharField(6) | 6-digit PIN |
| `status` | CharField(20) | PENDING/PAID/CONVERTED/EXPIRED |
| `items_snapshot` | JSONField | Order items |
| `total_amount` | DecimalField(10,2) | Order total |
| `expires_at` | DateTimeField | 24h expiry |
| `created_at` | DateTimeField | Creation timestamp |
| `converted_order` | OneToOneField(DineInOrder) | Converted order |

### Reservation

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `customer_phone` | CharField(20) | Customer phone |
| `customer_name` | CharField(200) | Customer name |
| `party_size` | PositiveSmallIntegerField | Number of guests |
| `reserved_for` | DateTimeField | Reserved time slot |
| `status` | CharField(20) | PENDING/CONFIRMED/SEATED/NO_SHOW/CANCELLED |
| `notes` | TextField | Special requests |
| `created_at` | DateTimeField | Creation timestamp |
| `table` | ForeignKey(Table) | Assigned table |
| `session` | OneToOneField(TableSession) | Linked session |

**State Machine:**
```
PENDING → CONFIRMED → SEATED/NO_SHOW/CANCELLED
```

### BillShare

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `payer_phone` | CharField(20) | Payer phone |
| `amount` | DecimalField(10,2) | Share amount |
| `items_snapshot` | JSONField | Items for this share |
| `status` | CharField(20) | PENDING/PAID/CANCELLED |
| `created_at` | DateTimeField | Creation timestamp |
| `session` | ForeignKey(TableSession) | Parent session |
| `payment_transaction` | ForeignKey(MpesaTransaction) | Linked payment |

---

## Bar Module

### Tab

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `customer_name` | CharField(200) | Walk-in customer name |
| `status` | CharField(20) | OPEN/BILL_REQUESTED/SETTLED |
| `opened_at` | DateTimeField | Opening timestamp |
| `settled_at` | DateTimeField | Settlement timestamp |
| `customer` | ForeignKey(User) | Registered customer |

**State Machine:**
```
OPEN → BILL_REQUESTED → SETTLED
```

### TabRound

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `round_number` | PositiveSmallIntegerField | | Round number (1-indexed) |
| `created_at` | DateTimeField | | Creation timestamp |
| `tab` | ForeignKey(Tab) | | Parent tab |

**Constraints:** UniqueConstraint(tab, round_number)

### TabItem

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(150) | Denormalized item name |
| `unit_price` | DecimalField(10,2) | Snapshotted price |
| `quantity` | PositiveSmallIntegerField | Quantity |
| `is_happy_hour` | BooleanField | Happy hour flag |
| `created_at` | DateTimeField | Creation timestamp |
| `removed_at` | DateTimeField | Removal timestamp |
| `removed_by_name` | CharField(200) | Staff name |
| `tab` | ForeignKey(Tab) | Parent tab |
| `round` | ForeignKey(TabRound) | Parent round |
| `menu_item` | ForeignKey(MenuItem) | Source menu item |
| `removed_by` | ForeignKey(User) | Staff who removed |

### AgeRestrictionLog

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `customer_phone` | CharField(20) | Customer phone |
| `acknowledged_at` | DateTimeField | Acknowledgement timestamp |
| `tab` | ForeignKey(Tab) | Parent tab |
| `customer` | ForeignKey(User) | Registered customer |

### HappyHour

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(100) | Happy hour name |
| `start_time` | TimeField | Start time |
| `end_time` | TimeField | End time |
| `discount_percent` | DecimalField(5,2) | Discount percentage |
| `days_of_week` | JSONField | ISO weekday ints (0=Mon..6=Sun) |
| `is_active` | BooleanField | Active flag |

**Custom Logic:**
- `is_active_now(current_dt)` checks time + day-of-week
- `apply_discount(price)` returns discounted price

### TabShare

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `payer_phone` | CharField(20) | Payer phone |
| `amount` | DecimalField(10,2) | Share amount |
| `item_ids` | JSONField | TabItem UUIDs (empty = percentage-based) |
| `percentage` | DecimalField(5,2) | Percentage share (nullable) |
| `status` | CharField(20) | PENDING/PAID/FAILED |
| `created_at` | DateTimeField | Creation timestamp |
| `tab` | ForeignKey(Tab) | Parent tab |
| `payment_transaction` | ForeignKey(MpesaTransaction) | Linked payment |

---

## Contracting Module

### Service

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(200) | Service name |
| `description` | TextField | Service description |
| `base_price` | DecimalField(10,2) | Base price |
| `duration_estimate` | PositiveIntegerField | Estimated duration (minutes) |
| `category` | CharField(50) | plumbing/electrical/cleaning/painting/landscaping/other |
| `is_active` | BooleanField | Active flag |

### AvailabilitySlot

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `start_time` | DateTimeField | Slot start |
| `end_time` | DateTimeField | Slot end |
| `is_booked` | BooleanField | Booking flag |
| `service` | ForeignKey(Service) | Parent service |

### ServiceBooking

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `customer_phone` | CharField(20) | Customer phone |
| `customer_name` | CharField(200) | Customer name |
| `notes` | TextField | Special requests |
| `status` | CharField(20) | PENDING/CONFIRMED/CANCELLED |
| `created_at` | DateTimeField | Creation timestamp |
| `service` | ForeignKey(Service) | Booked service |
| `slot` | OneToOneField(AvailabilitySlot) | Booked slot |

### QuoteRequest

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `customer_phone` | CharField(20) | Customer phone |
| `customer_name` | CharField(200) | Customer name |
| `description` | TextField | Request description |
| `status` | CharField(20) | OPEN/QUOTED/CLOSED |
| `created_at` | DateTimeField | Creation timestamp |
| `service` | ForeignKey(Service) | Related service |

### Quote

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `line_items` | JSONField | [{description, quantity, unit_price}] |
| `total_amount` | DecimalField(10,2) | Quote total |
| `valid_until` | DateField | Expiry date |
| `notes` | TextField | Additional notes |
| `status` | CharField(20) | QUOTED/ACCEPTED/REJECTED |
| `created_at` | DateTimeField | Creation timestamp |
| `quote_request` | OneToOneField(QuoteRequest) | Parent request |

### Job

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `title` | CharField(200) | Job title |
| `description` | TextField | Job description |
| `status` | CharField(20) | PENDING/IN_PROGRESS/COMPLETED/SETTLED |
| `created_at` | DateTimeField | Creation timestamp |
| `completed_at` | DateTimeField | Completion timestamp |
| `booking` | OneToOneField(ServiceBooking) | Source booking |
| `quote` | OneToOneField(Quote) | Source quote |
| `assigned_worker` | ForeignKey(User) | Assigned worker |

**State Machine:**
```
PENDING → IN_PROGRESS → COMPLETED → SETTLED
```

### JobMilestone

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `title` | CharField(200) | Milestone title |
| `description` | TextField | Milestone description |
| `status` | CharField(20) | PENDING/COMPLETED |
| `completion_photo` | ImageField | Completion photo (WebP) |
| `notes` | TextField | Completion notes |
| `completed_at` | DateTimeField | Completion timestamp |
| `position` | PositiveSmallIntegerField | Sort order |
| `created_at` | DateTimeField | Creation timestamp |
| `job` | ForeignKey(Job) | Parent job |

### Invoice

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `line_items` | JSONField | [{description, quantity, unit_price}] |
| `total_amount` | DecimalField(10,2) | Invoice total |
| `payment_status` | CharField(20) | UNPAID/PAID |
| `pdf_file` | FileField | Generated PDF |
| `shareable_token` | CharField(200) | HMAC-signed download token |
| `created_at` | DateTimeField | Creation timestamp |
| `paid_at` | DateTimeField | Payment timestamp |
| `job` | OneToOneField(Job) | Parent job |
| `payment_transaction` | ForeignKey(MpesaTransaction) | Linked payment |

---

## SaaS Module

### Plan

**Inherits:** models.Model (NOT TenantModel — global)

| Field | Type | Description |
|-------|------|-------------|
| `slug` | SlugField(50) | Unique identifier |
| `name` | CharField(100) | Plan name |
| `price_kes` | DecimalField(10,2) | Monthly price in KES |
| `billing_cycle` | CharField(10) | monthly/annual |
| `trial_days` | PositiveIntegerField | Trial period (default: 14) |
| `max_products` | PositiveIntegerField | Product limit (null = unlimited) |
| `max_orders_per_month` | PositiveIntegerField | Order limit (null = unlimited) |
| `max_staff` | PositiveIntegerField | Staff limit (null = unlimited) |
| `has_analytics` | BooleanField | Analytics feature flag |
| `has_qr_codes` | BooleanField | QR code feature flag |
| `has_ai_features` | BooleanField | AI feature flag |
| `has_whatsapp` | BooleanField | WhatsApp feature flag |
| `api_rate_limit` | IntegerField | Requests/min/store (default: 100) |
| `is_public` | BooleanField | Visible in plan list |
| `is_active` | BooleanField | Active flag |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |

### StoreSubscription

**Inherits:** models.Model (NOT TenantModel — cross-tenant)

| Field | Type | Description |
|-------|------|-------------|
| `status` | CharField(20) | trial/active/past_due/suspended/cancelled |
| `period_start` | DateField | Current period start |
| `period_end` | DateField | Current period end |
| `trial_ends_at` | DateField | Trial expiry |
| `past_due_since` | DateField | Past due since |
| `suspended_at` | DateTimeField | Suspension timestamp |
| `cancelled_at` | DateTimeField | Cancellation timestamp |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |
| `store` | OneToOneField(Store) | Parent store |
| `plan` | ForeignKey(Plan) | Current plan |
| `current_payment_transaction` | ForeignKey(MpesaTransaction) | Last payment |

**State Machine:**
```
TRIAL → ACTIVE → PAST_DUE → SUSPENDED/CANCELLED
```

---

## Analytics Module

### AdminPIIAccessLog

**Inherits:** models.Model (NOT TenantModel — audit log)

| Field | Type | Description |
|-------|------|-------------|
| `record_type` | CharField(100) | Record type accessed |
| `record_id` | CharField(255) | Record ID accessed |
| `accessed_at` | DateTimeField | Access timestamp |
| `path` | CharField(500) | Request path |
| `method` | CharField(10) | HTTP method |
| `user` | ForeignKey(User) | Accessing user |
| `store` | ForeignKey(Store) | Store context |

### DailyRevenueSummary

**Inherits:** models.Model (NOT TenantModel — pre-aggregated)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `date` | DateField | indexed | Summary date |
| `total_revenue` | DecimalField(14,2) | | Total revenue |
| `order_count` | PositiveIntegerField | | Order count |
| `aov` | DecimalField(14,2) | | Average order value |
| `amount_usd` | DecimalField(14,2) | | USD-normalized revenue |
| `top_products` | JSONField | | [{product_id, name, revenue}] |
| `store` | ForeignKey(Store) | | Parent store |

**Constraints:** unique_together(store, date)

### HourlyOrderSummary

**Inherits:** models.Model (NOT TenantModel — pre-aggregated)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `date` | DateField | indexed | Summary date |
| `hour` | PositiveSmallIntegerField | | Hour (0-23 local) |
| `order_count` | PositiveIntegerField | | Order count |
| `revenue` | DecimalField(14,2) | | Revenue |
| `store` | ForeignKey(Store) | | Parent store |

**Constraints:** unique_together(store, date, hour)

### AIEvent

**Inherits:** models.Model (NOT TenantModel — append-only)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `event_type` | CharField(30) | indexed | product_view/cart_add/cart_remove/search/order_complete |
| `entity_id` | CharField(255) | | Product ID, search query, or order ID |
| `metadata` | JSONField | | Event-specific data |
| `occurred_at` | DateTimeField | indexed | Event timestamp |
| `store` | ForeignKey(Store) | | Parent store |
| `customer` | ForeignKey(User) | | Customer (nullable) |

**Custom Logic:**
- `save()` enforces append-only (rejects updates to existing records)

### TenantHealthSnapshot

**Inherits:** models.Model (NOT TenantModel — platform monitoring)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `date` | DateField | indexed | Snapshot date |
| `gmv` | DecimalField(14,2) | | Gross merchandise value (KES) |
| `gmv_usd` | DecimalField(14,2) | | GMV in USD |
| `order_count` | PositiveIntegerField | | Order count |
| `subscription_status` | CharField(30) | | Subscription status |
| `is_healthy` | BooleanField | | Health flag |
| `store` | ForeignKey(Store) | | Parent store |

**Constraints:** unique_together(store, date)

### StoreFirstOrderEvent

**Inherits:** models.Model (NOT TenantModel — milestone)

| Field | Type | Description |
|-------|------|-------------|
| `first_order_amount` | DecimalField(10,2) | First order amount |
| `occurred_at` | DateTimeField | Event timestamp |
| `store` | OneToOneField(Store) | Parent store |
| `order` | ForeignKey(Order) | First order |

---

## Loyalty Module

### LoyaltyAccount

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `customer_phone` | CharField(30) | indexed | Customer phone |
| `points_balance` | IntegerField | | Current balance |
| `lifetime_earned` | IntegerField | | Total earned |
| `customer` | ForeignKey(User) | | Registered customer |

**Constraints:** unique_together(store, customer_phone)

**Custom Logic:**
- `earn(points, source, reference)` adds points + creates transaction
- `redeem(points, reference)` deducts points + creates transaction

### PointsTransaction

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `delta` | IntegerField | | Positive = earned, negative = redeemed |
| `balance_after` | IntegerField | | Balance after transaction |
| `source` | CharField(20) | indexed | order/redemption/manual/expiry |
| `reference` | CharField(255) | | Related reference |
| `occurred_at` | DateTimeField | indexed | Transaction timestamp |
| `account` | ForeignKey(LoyaltyAccount) | | Parent account |

**Custom Logic:**
- `save()` enforces append-only (rejects updates)

### StampCard

**Inherits:** TenantModel

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(100) | Card name |
| `stamps_required` | PositiveIntegerField | Threshold (default: 10) |
| `reward_description` | CharField(255) | Reward description |
| `points_per_stamp` | IntegerField | Bonus points on completion |
| `is_active` | BooleanField | Active flag |

### CustomerStampCard

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `customer_phone` | CharField(30) | indexed | Customer phone |
| `stamps_count` | PositiveIntegerField | | Current stamps |
| `redeemed_count` | PositiveIntegerField | | Times redeemed |
| `last_stamp_at` | DateTimeField | | Last stamp timestamp |
| `stamp_card` | ForeignKey(StampCard) | | Parent card |
| `customer` | ForeignKey(User) | | Customer |

**Constraints:** unique_together(store, stamp_card, customer_phone)

**Custom Logic:**
- `add_stamp(order_id)` increments stamps, triggers reward if threshold reached

### CustomerStamp

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `order_reference` | CharField(255) | | Related order |
| `earned_at` | DateTimeField | indexed | Stamp timestamp |
| `customer_card` | ForeignKey(CustomerStampCard) | | Parent card |

### CustomerProfile

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `customer_phone` | CharField(30) | indexed | Customer phone |
| `customer_email` | EmailField | | Customer email |
| `customer_name` | CharField(255) | | Customer name |
| `order_count` | PositiveIntegerField | | Total orders |
| `total_spent` | DecimalField(14,2) | | Total spent |
| `first_order_at` | DateTimeField | | First order timestamp |
| `last_order_at` | DateTimeField | | Last order timestamp |
| `customer` | ForeignKey(User) | | Customer |

**Constraints:** unique_together(store, customer_phone)

**Custom Logic:**
- `record_order(amount, ordered_at)` updates RFM metrics

---

## Notifications Module

### WhatsAppMessage

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `recipient_phone` | CharField(30) | indexed | Recipient phone |
| `template` | CharField(50) | | Message template |
| `message_body` | TextField | | Message content |
| `status` | CharField(20) | indexed | queued/sent/failed |
| `external_message_id` | CharField(255) | | External ID |
| `error_detail` | TextField | | Error details |
| `queued_at` | DateTimeField | | Queue timestamp |
| `sent_at` | DateTimeField | | Send timestamp |

### WhatsAppInboundMessage

**Inherits:** TenantModel

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `sender_phone` | CharField(30) | indexed | Sender phone |
| `raw_body` | TextField | | Raw message |
| `parsed_intent` | CharField(50) | | order/menu/status/unknown |
| `response_sent` | BooleanField | | Response flag |
| `received_at` | DateTimeField | indexed | Receipt timestamp |

### FCMDevice

**Inherits:** models.Model (NOT TenantModel — cross-tenant)

| Field | Type | Description |
|-------|------|-------------|
| `registration_id` | TextField | FCM device token |
| `platform` | CharField(10) | android/ios/web |
| `is_active` | BooleanField | Active flag |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last update timestamp |
| `platform_user` | ForeignKey(PlatformUser) | Owner |

**Constraints:** unique_together(platform_user, registration_id)

---

## Users Module

### PlatformUser

**Inherits:** models.Model (NOT TenantModel — cross-tenant)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `email` | EmailField | unique, indexed | Email address |
| `password` | CharField(128) | | Hashed password |
| `phone` | CharField(30) | unique, nullable | Phone number |
| `full_name` | CharField(255) | | Full name |
| `avatar_url` | URLField | | Avatar URL |
| `google_sub` | CharField(255) | unique, nullable | Google OAuth subject |
| `is_active` | BooleanField | | Active flag |
| `created_at` | DateTimeField | | Creation timestamp |
| `updated_at` | DateTimeField | | Last update timestamp |

### User

**Inherits:** AbstractUser

| Field | Type | Description |
|-------|------|-------------|
| `email` | EmailField | Email (unique per store) |
| `role` | CharField(20) | platform_admin/store_owner/store_manager/customer |
| `store` | ForeignKey(Store) | Store (null for platform_admin) |
| `platform_user` | ForeignKey(PlatformUser) | Linked platform user |

**Constraints:**
- UniqueConstraint(email, store) — unique per store
- UniqueConstraint(email) WHERE store IS NULL — prevents duplicate platform_admin emails

---

## Model Statistics

| Category | Count |
|----------|-------|
| Total model classes | 47 |
| Models inheriting TenantModel | 33 |
| Models inheriting SoftDeleteModel | 1 |
| Models on AbstractUser | 1 |
| Models on plain models.Model | 12 |

### Models by App

| App | Models |
|-----|--------|
| core | SoftDeleteModel, TenantModel |
| store | Store, StoreSettings, StoreTheme |
| product | Category, Product, Variant, ProductImage |
| order | Order, CartSnapshot |
| payment | MpesaTransaction, CardTransaction |
| restaurant | MenuSection, MenuItem, ModifierGroup, Modifier, Table, TableSession, DineInOrder, KitchenTicket, PendingOrder, Reservation, BillShare |
| bar | Tab, TabRound, TabItem, AgeRestrictionLog, HappyHour, TabShare |
| contracting | Service, AvailabilitySlot, ServiceBooking, QuoteRequest, Quote, Job, JobMilestone, Invoice |
| saas | Plan, StoreSubscription |
| analytics | AdminPIIAccessLog, DailyRevenueSummary, HourlyOrderSummary, AIEvent, TenantHealthSnapshot, StoreFirstOrderEvent |
| ai | (none — namespace placeholder) |
| loyalty | LoyaltyAccount, PointsTransaction, StampCard, CustomerStampCard, CustomerStamp, CustomerProfile |
| notifications | WhatsAppMessage, WhatsAppInboundMessage, FCMDevice |
| users | PlatformUser, User |
| inventory | (empty file) |
