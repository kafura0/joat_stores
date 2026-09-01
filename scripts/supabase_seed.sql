-- Supabase SQL Editor: Run this to set up schema + seed data
-- Generated for joat_stores POS deployment

-- Drop existing tables (order matters for foreign keys)
DROP TABLE IF EXISTS bar_tabshare CASCADE;
DROP TABLE IF EXISTS bar_tabitem CASCADE;
DROP TABLE IF EXISTS bar_tabround CASCADE;
DROP TABLE IF EXISTS bar_tab CASCADE;
DROP TABLE IF EXISTS bar_happyhour CASCADE;
DROP TABLE IF EXISTS bar_agerestrictionlog CASCADE;
DROP TABLE IF EXISTS restaurant_kitchenticket CASCADE;
DROP TABLE IF EXISTS restaurant_dineinorder CASCADE;
DROP TABLE IF EXISTS restaurant_pendingorder CASCADE;
DROP TABLE IF EXISTS restaurant_reservation CASCADE;
DROP TABLE IF EXISTS restaurant_billshare CASCADE;
DROP TABLE IF EXISTS restaurant_tablesession CASCADE;
DROP TABLE IF EXISTS restaurant_table CASCADE;
DROP TABLE IF EXISTS restaurant_menuitem CASCADE;
DROP TABLE IF EXISTS restaurant_modifiergroup CASCADE;
DROP TABLE IF EXISTS restaurant_modifier CASCADE;
DROP TABLE IF EXISTS restaurant_menusection CASCADE;
DROP TABLE IF EXISTS order_cartsnapshot CASCADE;
DROP TABLE IF EXISTS order_order CASCADE;
DROP TABLE IF EXISTS product_productimage CASCADE;
DROP TABLE IF EXISTS product_variant CASCADE;
DROP TABLE IF EXISTS product_product CASCADE;
DROP TABLE IF EXISTS product_category CASCADE;
DROP TABLE IF EXISTS payment_cardtransaction CASCADE;
DROP TABLE IF EXISTS payment_mpesatransaction CASCADE;
DROP TABLE IF EXISTS saas_storesubscription CASCADE;
DROP TABLE IF EXISTS analytics_dailyrevenuesummary CASCADE;
DROP TABLE IF EXISTS analytics_hourlyordersummary CASCADE;
DROP TABLE IF EXISTS users_user_groups CASCADE;
DROP TABLE IF EXISTS users_user_user_permissions CASCADE;
DROP TABLE IF EXISTS users_user CASCADE;
DROP TABLE IF EXISTS users_platformuser CASCADE;
DROP TABLE IF EXISTS store_storetheme CASCADE;
DROP TABLE IF EXISTS store_storesettings CASCADE;
DROP TABLE IF EXISTS store_store CASCADE;
DROP TABLE IF EXISTS saas_plan CASCADE;
DROP TABLE IF EXISTS auth_group_permissions CASCADE;
DROP TABLE IF EXISTS auth_group CASCADE;
DROP TABLE IF EXISTS auth_permission CASCADE;
DROP TABLE IF EXISTS django_migrations CASCADE;
DROP TABLE IF EXISTS django_content_type CASCADE;

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ========================================
-- 1. DJANGO SYSTEM TABLES
-- ========================================

CREATE TABLE IF NOT EXISTS django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    UNIQUE(app_label, model)
);

CREATE TABLE IF NOT EXISTS auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id),
    codename VARCHAR(100) NOT NULL,
    UNIQUE(content_type_id, codename)
);

CREATE TABLE IF NOT EXISTS auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS auth_group_permissions (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES auth_group(id),
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id),
    UNIQUE(group_id, permission_id)
);

CREATE TABLE IF NOT EXISTS django_migrations (
    id SERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ========================================
-- 2. STORE (TENANT ROOT)
-- ========================================

CREATE TABLE store_store (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    domain VARCHAR(253) NOT NULL UNIQUE,
    tenant_type VARCHAR(20) NOT NULL DEFAULT 'retail',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    currency VARCHAR(3) NOT NULL DEFAULT 'KES',
    payment_methods VARCHAR(50)[] DEFAULT '{}',
    country VARCHAR(2) NOT NULL DEFAULT 'KE',
    timezone VARCHAR(63) NOT NULL DEFAULT 'Africa/Nairobi',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE store_storesettings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    tagline VARCHAR(255) NOT NULL DEFAULT '',
    logo_url VARCHAR(200) NOT NULL DEFAULT '',
    low_stock_threshold INTEGER NOT NULL DEFAULT 5,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE store_storetheme (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    preset_slug VARCHAR(30) NOT NULL DEFAULT 'modern',
    template_style VARCHAR(30) NOT NULL DEFAULT 'modern',
    primary_color VARCHAR(20) NOT NULL DEFAULT '#1a1a1a',
    secondary_color VARCHAR(20) NOT NULL DEFAULT '#6b7280',
    accent_color VARCHAR(20) NOT NULL DEFAULT '#e63946',
    background_color VARCHAR(20) NOT NULL DEFAULT '#ffffff',
    surface_color VARCHAR(20) NOT NULL DEFAULT '#f9fafb',
    text_primary_color VARCHAR(20) NOT NULL DEFAULT '#111827',
    text_secondary_color VARCHAR(20) NOT NULL DEFAULT '#6b7280',
    success_color VARCHAR(20) NOT NULL DEFAULT '#16a34a',
    error_color VARCHAR(20) NOT NULL DEFAULT '#dc2626',
    warning_color VARCHAR(20) NOT NULL DEFAULT '#f59e0b',
    header_background VARCHAR(20) NOT NULL DEFAULT '#1a1a1a',
    header_text_color VARCHAR(20) NOT NULL DEFAULT '#ffffff',
    footer_background VARCHAR(20) NOT NULL DEFAULT '#1f2937',
    footer_text_color VARCHAR(20) NOT NULL DEFAULT '#f3f4f6',
    font_family_heading VARCHAR(100) NOT NULL DEFAULT 'Inter',
    font_family_body VARCHAR(100) NOT NULL DEFAULT 'Inter',
    font_size_base VARCHAR(10) NOT NULL DEFAULT '1rem',
    font_size_scale NUMERIC(4,2) NOT NULL DEFAULT 1.25,
    section_padding_y VARCHAR(10) NOT NULL DEFAULT '4rem',
    card_padding VARCHAR(10) NOT NULL DEFAULT '1.5rem',
    container_max_width VARCHAR(10) NOT NULL DEFAULT '1280px',
    radius_sm VARCHAR(10) NOT NULL DEFAULT '0.25rem',
    radius_md VARCHAR(10) NOT NULL DEFAULT '0.5rem',
    radius_lg VARCHAR(10) NOT NULL DEFAULT '0.75rem',
    radius_full VARCHAR(10) NOT NULL DEFAULT '9999px',
    shadow_sm VARCHAR(50) NOT NULL DEFAULT '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    shadow_md VARCHAR(50) NOT NULL DEFAULT '0 4px 6px -1px rgb(0 0 0 / 0.1)',
    shadow_lg VARCHAR(50) NOT NULL DEFAULT '0 10px 15px -3px rgb(0 0 0 / 0.1)',
    announcement_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    announcement_text VARCHAR(500) NOT NULL DEFAULT '',
    custom_css TEXT NOT NULL DEFAULT '',
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);

-- ========================================
-- 3. USERS
-- ========================================

CREATE TABLE users_platformuser (
    id SERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,
    phone VARCHAR(30) UNIQUE,
    full_name VARCHAR(255) NOT NULL DEFAULT '',
    avatar_url VARCHAR(200) NOT NULL DEFAULT '',
    google_sub VARCHAR(255) UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE users_user (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    email VARCHAR(254) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer',
    store_id UUID REFERENCES store_store(id) ON DELETE CASCADE,
    platform_user_id INTEGER REFERENCES users_platformuser(id) ON DELETE SET NULL,
    CONSTRAINT uq_user_email_store UNIQUE (email, store_id)
);
CREATE UNIQUE INDEX uq_platform_admin_email ON users_user(email) WHERE store_id IS NULL;

CREATE TABLE users_user_groups (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    UNIQUE(user_id, group_id)
);

CREATE TABLE users_user_user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users_user(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    UNIQUE(user_id, permission_id)
);

-- ========================================
-- 4. SAAS
-- ========================================

CREATE TABLE saas_plan (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    price_kes NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    billing_cycle VARCHAR(10) NOT NULL DEFAULT 'monthly',
    trial_days INTEGER NOT NULL DEFAULT 14,
    max_products INTEGER,
    max_orders_per_month INTEGER,
    max_staff INTEGER,
    has_analytics BOOLEAN NOT NULL DEFAULT FALSE,
    has_qr_codes BOOLEAN NOT NULL DEFAULT TRUE,
    has_ai_features BOOLEAN NOT NULL DEFAULT FALSE,
    has_whatsapp BOOLEAN NOT NULL DEFAULT FALSE,
    api_rate_limit INTEGER NOT NULL DEFAULT 100,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE payment_mpesatransaction (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    reference VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'STK_PUSH_INITIATED',
    checkout_request_id VARCHAR(100) NOT NULL DEFAULT '',
    mpesa_receipt_number VARCHAR(50) UNIQUE,
    merchant_request_id VARCHAR(100) NOT NULL DEFAULT '',
    initiated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    reversal_reason VARCHAR(255) NOT NULL DEFAULT '',
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX payment_mpesa_store_ref_idx ON payment_mpesatransaction(store_id, reference);

CREATE TABLE saas_storesubscription (
    id SERIAL PRIMARY KEY,
    store_id UUID NOT NULL UNIQUE REFERENCES store_store(id) ON DELETE CASCADE,
    plan_id INTEGER REFERENCES saas_plan(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'trial',
    period_start DATE,
    period_end DATE,
    trial_ends_at DATE,
    current_payment_transaction_id UUID REFERENCES payment_mpesatransaction(id) ON DELETE SET NULL,
    past_due_since DATE,
    suspended_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX saas_storesubscription_status_idx ON saas_storesubscription(status);
CREATE INDEX saas_storesubscription_period_end_idx ON saas_storesubscription(period_end);

-- ========================================
-- 5. PRODUCTS
-- ========================================

CREATE TABLE product_category (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    parent_id UUID REFERENCES product_category(id) ON DELETE SET NULL,
    position INTEGER NOT NULL DEFAULT 0,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_product_category_parent ON product_category(store_id, parent_id);

CREATE TABLE product_product (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    category_id UUID REFERENCES product_category(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    attribute_names JSONB NOT NULL DEFAULT '[]',
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_product_store_available ON product_product(store_id, is_available);
CREATE INDEX idx_product_store_category ON product_product(store_id, category_id);

CREATE TABLE product_variant (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES product_product(id) ON DELETE CASCADE,
    attribute_values JSONB NOT NULL DEFAULT '{}',
    price NUMERIC(10,2) NOT NULL CHECK (price >= 0.00),
    inventory_count INTEGER NOT NULL DEFAULT 0,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    sku VARCHAR(100) NOT NULL DEFAULT '',
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_variant_store_product ON product_variant(store_id, product_id);
CREATE INDEX idx_variant_available ON product_variant(store_id, is_available);

CREATE TABLE product_productimage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES product_product(id) ON DELETE CASCADE,
    variant_id UUID REFERENCES product_variant(id) ON DELETE SET NULL,
    image VARCHAR(100) NOT NULL,
    alt_text VARCHAR(255) NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_productimage_product ON product_productimage(store_id, product_id);

-- ========================================
-- 6. ORDERS
-- ========================================

CREATE TABLE order_order (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    customer_phone VARCHAR(30) NOT NULL,
    customer_name VARCHAR(255) NOT NULL DEFAULT '',
    customer_email VARCHAR(254) NOT NULL DEFAULT '',
    delivery_address JSONB,
    items_snapshot JSONB NOT NULL DEFAULT '[]',
    total_amount NUMERIC(10,2) NOT NULL CHECK (total_amount >= 0.00),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    payment_transaction_id UUID REFERENCES payment_mpesatransaction(id) ON DELETE SET NULL,
    customer_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    fulfilled_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_order_store_status ON order_order(store_id, status);
CREATE INDEX idx_order_store_phone ON order_order(store_id, customer_phone);

-- ========================================
-- 7. RESTAURANT
-- ========================================

CREATE TABLE restaurant_menusection (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    position SMALLINT NOT NULL DEFAULT 0,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT rst_msection_store_name UNIQUE (store_id, name)
);
CREATE INDEX idx_rst_msection_store_pos ON restaurant_menusection(store_id, position);

CREATE TABLE restaurant_menuitem (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    section_id UUID NOT NULL REFERENCES restaurant_menusection(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price NUMERIC(10,2) NOT NULL CHECK (price >= 0.00),
    contains_allergens BOOLEAN NOT NULL DEFAULT FALSE,
    allergen_description TEXT NOT NULL DEFAULT '',
    is_age_restricted BOOLEAN NOT NULL DEFAULT FALSE,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    available_from TIME,
    available_until TIME,
    position SMALLINT NOT NULL DEFAULT 0,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_rst_mitem_store_section ON restaurant_menuitem(store_id, section_id);
CREATE INDEX idx_rst_mitem_store_avail ON restaurant_menuitem(store_id, is_available);

CREATE TABLE restaurant_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    number SMALLINT NOT NULL,
    name VARCHAR(50) NOT NULL DEFAULT '',
    capacity SMALLINT NOT NULL DEFAULT 2,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT rst_table_store_number UNIQUE (store_id, number)
);
CREATE INDEX idx_rst_table_store_active ON restaurant_table(store_id, is_active);

CREATE TABLE restaurant_tablesession (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    table_id UUID NOT NULL REFERENCES restaurant_table(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    assigned_waiter_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX rst_tsess_store_status ON restaurant_tablesession(store_id, status);
CREATE INDEX rst_tsess_table_status ON restaurant_tablesession(table_id, status);

CREATE TABLE payment_cardtransaction (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    reference VARCHAR(100) NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'kes',
    status VARCHAR(30) NOT NULL DEFAULT 'PI_CREATED',
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    stripe_client_secret TEXT NOT NULL DEFAULT '',
    provider VARCHAR(20) NOT NULL DEFAULT 'stripe',
    customer_email VARCHAR(254) NOT NULL DEFAULT '',
    initiated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    failure_reason TEXT NOT NULL DEFAULT '',
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX payment_card_store_ref_idx ON payment_cardtransaction(store_id, reference);

CREATE TABLE restaurant_dineinorder (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    session_id UUID REFERENCES restaurant_tablesession(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    items_snapshot JSONB NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL CHECK (total_amount >= 0.00),
    order_type VARCHAR(20) NOT NULL DEFAULT 'dine_in',
    pickup_reference VARCHAR(20) NOT NULL DEFAULT '',
    placed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    payment_transaction_id UUID REFERENCES payment_mpesatransaction(id) ON DELETE SET NULL,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX rst_dinord_store_status ON restaurant_dineinorder(store_id, status);
CREATE INDEX idx_rst_dineinorder_session ON restaurant_dineinorder(session_id);

CREATE TABLE restaurant_kitchenticket (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    order_id UUID NOT NULL UNIQUE REFERENCES restaurant_dineinorder(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    items_snapshot JSONB NOT NULL,
    waiter_name VARCHAR(200) NOT NULL DEFAULT '',
    table_number SMALLINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX rst_kittkt_store_status ON restaurant_kitchenticket(store_id, status);

-- ========================================
-- 8. BAR
-- ========================================

CREATE TABLE bar_tab (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    customer_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,
    customer_name VARCHAR(200) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    settled_at TIMESTAMP WITH TIME ZONE,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_bar_tab_store_status ON bar_tab(store_id, status);

CREATE TABLE bar_tabround (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    tab_id UUID NOT NULL REFERENCES bar_tab(id) ON DELETE CASCADE,
    round_number SMALLINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_bar_tabround_tab_round_number UNIQUE (tab_id, round_number)
);

CREATE TABLE bar_tabitem (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    tab_id UUID NOT NULL REFERENCES bar_tab(id) ON DELETE CASCADE,
    round_id UUID NOT NULL REFERENCES bar_tabround(id) ON DELETE CASCADE,
    menu_item_id UUID NOT NULL REFERENCES restaurant_menuitem(id) ON DELETE RESTRICT,
    name VARCHAR(150) NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0.00),
    quantity SMALLINT NOT NULL DEFAULT 1,
    is_happy_hour BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    removed_at TIMESTAMP WITH TIME ZONE,
    removed_by_id INTEGER REFERENCES users_user(id) ON DELETE SET NULL,
    removed_by_name VARCHAR(200) NOT NULL DEFAULT '',
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_bar_tabitem_tab_removed ON bar_tabitem(tab_id, removed_at);

CREATE TABLE bar_happyhour (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    discount_percent NUMERIC(5,2) NOT NULL CHECK (discount_percent >= 0 AND discount_percent <= 100),
    days_of_week JSONB NOT NULL DEFAULT '[]',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_bar_happyhour_store_active ON bar_tabitem(store_id, is_happy_hour);

CREATE TABLE bar_tabshare (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    tab_id UUID NOT NULL REFERENCES bar_tab(id) ON DELETE CASCADE,
    payer_phone VARCHAR(20) NOT NULL,
    amount NUMERIC(10,2) NOT NULL CHECK (amount >= 0.00),
    item_ids JSONB NOT NULL DEFAULT '[]',
    percentage NUMERIC(5,2),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    payment_transaction_id UUID REFERENCES payment_mpesatransaction(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted TIMESTAMP WITH TIME ZONE,
    deleted_by_cascade BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_bar_tabshare_tab_status ON bar_tabshare(store_id, tab_id, status);

-- ========================================
-- 9. ANALYTICS
-- ========================================

CREATE TABLE analytics_dailyrevenuesummary (
    id SERIAL PRIMARY KEY,
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_revenue NUMERIC(14,2) NOT NULL DEFAULT 0,
    order_count INTEGER NOT NULL DEFAULT 0,
    aov NUMERIC(14,2),
    amount_usd NUMERIC(14,2) NOT NULL DEFAULT 0,
    top_products JSONB NOT NULL DEFAULT '[]',
    CONSTRAINT analytics_dailyrevenuesummary_store_date_unique UNIQUE (store_id, date)
);
CREATE INDEX idx_analytics_drs_store_date ON analytics_dailyrevenuesummary(store_id, date);

CREATE TABLE analytics_hourlyordersummary (
    id SERIAL PRIMARY KEY,
    store_id UUID NOT NULL REFERENCES store_store(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    hour SMALLINT NOT NULL CHECK (hour >= 0 AND hour <= 23),
    order_count INTEGER NOT NULL DEFAULT 0,
    revenue NUMERIC(14,2) NOT NULL DEFAULT 0,
    CONSTRAINT analytics_hourlyordersummary_store_date_hour_unique UNIQUE (store_id, date, hour)
);
CREATE INDEX idx_analytics_hos_store_date ON analytics_hourlyordersummary(store_id, date);

-- ========================================
-- SEED DATA
-- ========================================

-- Plans
INSERT INTO saas_plan (slug, name, price_kes, billing_cycle, trial_days, max_products, max_orders_per_month, max_staff, has_analytics, has_qr_codes, has_ai_features, has_whatsapp, api_rate_limit, is_public, is_active, created_at, updated_at)
VALUES
('free', 'Free', 0.00, 'monthly', 14, 20, 50, 1, FALSE, FALSE, FALSE, FALSE, 30, TRUE, TRUE, NOW(), NOW()),
('starter', 'Starter', 1500.00, 'monthly', 14, 100, 500, 3, TRUE, TRUE, FALSE, FALSE, 60, TRUE, TRUE, NOW(), NOW()),
('growth', 'Growth', 4500.00, 'monthly', 14, 500, 2000, 10, TRUE, TRUE, TRUE, TRUE, 120, TRUE, TRUE, NOW(), NOW()),
('pro', 'Pro', 12000.00, 'monthly', 14, NULL, NULL, NULL, TRUE, TRUE, TRUE, TRUE, 300, TRUE, TRUE, NOW(), NOW());

-- Stores
INSERT INTO store_store (id, name, slug, domain, tenant_type, status, currency, payment_methods, country, timezone, created_at, updated_at)
VALUES
('a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'JOAT Demo Bar', 'joat-demo-bar', 'demo-bar.joat.com', 'bar', 'active', 'KES', ARRAY['mpesa'], 'KE', 'Africa/Nairobi', NOW(), NOW()),
('a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'JOAT Demo Restaurant', 'joat-demo-restaurant', 'demo-restaurant.joat.com', 'restaurant', 'active', 'KES', ARRAY['mpesa'], 'KE', 'Africa/Nairobi', NOW(), NOW());

-- Store Settings
INSERT INTO store_storesettings (id, store_id, low_stock_threshold, deleted, deleted_by_cascade)
VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 2, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 3, NULL, FALSE);

-- Store Themes
INSERT INTO store_storetheme (id, store_id, preset_slug, template_style, deleted, deleted_by_cascade)
VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'bold', 'bold', NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'classic', 'classic', NULL, FALSE);

-- Subscriptions (trial)
INSERT INTO saas_storesubscription (store_id, plan_id, status, trial_ends_at, created_at, updated_at)
VALUES
('a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM saas_plan WHERE slug='starter'), 'trial', (NOW() + INTERVAL '14 days'), NOW(), NOW()),
('a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM saas_plan WHERE slug='pro'), 'trial', (NOW() + INTERVAL '14 days'), NOW(), NOW());

-- Platform Admin (no store)
INSERT INTO users_user (password, is_superuser, first_name, last_name, is_staff, is_active, date_joined, email, role, store_id)
VALUES ('pbkdf2_sha256$1000000$dVmoPrVV2lcUoFw7dr2GXG$oid9yxjK81oNPZyJx2za8DIMuSI5z95NBiMJatRqieA=', TRUE, 'Platform', 'Admin', TRUE, TRUE, NOW(), 'admin@joat.com', 'platform_admin', NULL);

-- Store Owners
INSERT INTO users_user (password, is_superuser, first_name, last_name, is_staff, is_active, date_joined, email, role, store_id)
VALUES
('pbkdf2_sha256$1000000$dVmoPrVV2lcUoFw7dr2GXG$oid9yxjK81oNPZyJx2za8DIMuSI5z95NBiMJatRqieA=', FALSE, 'Bar', 'Owner', FALSE, TRUE, NOW(), 'bar@joat.com', 'store_owner', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801'),
('pbkdf2_sha256$1000000$dVmoPrVV2lcUoFw7dr2GXG$oid9yxjK81oNPZyJx2za8DIMuSI5z95NBiMJatRqieA=', FALSE, 'Restaurant', 'Owner', FALSE, TRUE, NOW(), 'restaurant@joat.com', 'store_owner', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802');

-- ========================================
-- BAR MENU
-- ========================================

-- Bar Menu Sections
INSERT INTO restaurant_menusection (id, store_id, name, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Beers', 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Spirits', 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Wine', 2, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Cocktails', 3, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Non-Alcoholic', 4, NULL, FALSE);

-- Bar Menu Items (Beers)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_age_restricted, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Beers' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Tusker Lager', 250.00, TRUE, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Beers' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Guinness Stout', 300.00, TRUE, TRUE, 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Beers' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'White Cap Lager', 280.00, TRUE, TRUE, 2, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Beers' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Heineken', 350.00, TRUE, TRUE, 3, NULL, FALSE);

-- Bar Menu Items (Spirits)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_age_restricted, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Spirits' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Johnnie Walker Red', 500.00, TRUE, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Spirits' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Jameson', 600.00, TRUE, TRUE, 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Spirits' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Smirnoff Vodka', 450.00, TRUE, TRUE, 2, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Spirits' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Bacardi Rum', 450.00, TRUE, TRUE, 3, NULL, FALSE);

-- Bar Menu Items (Cocktails)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_age_restricted, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Cocktails' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Mojito', 600.00, TRUE, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Cocktails' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Dawa', 500.00, TRUE, TRUE, 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Cocktails' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Gin & Tonic', 550.00, TRUE, TRUE, 2, NULL, FALSE);

-- Bar Menu Items (Non-Alcoholic)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_age_restricted, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Non-Alcoholic' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Fresh Juice', 150.00, FALSE, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Non-Alcoholic' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Soda', 100.00, FALSE, TRUE, 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM restaurant_menusection WHERE name='Non-Alcoholic' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567801'), 'Red Bull', 200.00, FALSE, TRUE, 2, NULL, FALSE);

-- Bar Tables
INSERT INTO restaurant_table (id, store_id, number, name, capacity, is_active, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 1, 'Window Seat', 2, TRUE, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 2, 'Corner Booth', 4, TRUE, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 3, 'Bar Counter', 6, TRUE, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 4, 'VIP Lounge', 8, TRUE, NULL, FALSE);

-- ========================================
-- RESTAURANT MENU
-- ========================================

-- Restaurant Menu Sections
INSERT INTO restaurant_menusection (id, store_id, name, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Starters', 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Mains', 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Pizzas', 2, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Drinks', 3, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Desserts', 4, NULL, FALSE);

-- Restaurant Menu Items (Starters)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Starters' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Chicken Wings', 450.00, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Starters' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Samosas (3)', 200.00, TRUE, 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Starters' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Soup of the Day', 250.00, TRUE, 2, NULL, FALSE);

-- Restaurant Menu Items (Mains)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Mains' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Nyama Choma', 800.00, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Mains' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Grilled Tilapia', 900.00, TRUE, 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Mains' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Biryani', 700.00, TRUE, 2, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Mains' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Beef Burger', 650.00, TRUE, 3, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Mains' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Vegetable Stir Fry', 500.00, TRUE, 4, NULL, FALSE);

-- Restaurant Menu Items (Pizzas)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Pizzas' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Margherita', 600.00, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Pizzas' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'BBQ Chicken', 750.00, TRUE, 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Pizzas' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Pepperoni', 700.00, TRUE, 2, NULL, FALSE);

-- Restaurant Menu Items (Drinks)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Drinks' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Fresh Juice', 150.00, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Drinks' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Soda', 100.00, TRUE, 1, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Drinks' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Water', 50.00, TRUE, 2, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Drinks' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Chai', 80.00, TRUE, 3, NULL, FALSE);

-- Restaurant Menu Items (Desserts)
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_available, position, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Desserts' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Chocolate Lava Cake', 400.00, TRUE, 0, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM restaurant_menusection WHERE name='Desserts' AND store_id='a1b2c3d4-e5f6-7890-abcd-ef1234567802'), 'Fruit Salad', 250.00, TRUE, 1, NULL, FALSE);

-- Restaurant Tables
INSERT INTO restaurant_table (id, store_id, number, name, capacity, is_active, deleted, deleted_by_cascade) VALUES
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 1, 'Table 1', 2, TRUE, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 2, 'Table 2', 4, TRUE, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 3, 'Table 3', 4, TRUE, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 4, 'Terrace 1', 6, TRUE, NULL, FALSE),
(uuid_generate_v4(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 5, 'Terrace 2', 8, TRUE, NULL, FALSE);
