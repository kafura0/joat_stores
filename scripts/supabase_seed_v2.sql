-- STEP 2: Seed data AFTER Django migrations have created all tables
-- Run this in Supabase SQL Editor AFTER Render deploy succeeds

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
('a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'JOAT Demo Bar', 'joat-demo-bar', 'demo-bar.joat.com', 'bar', 'active', 'KES', ARRAY['mpesa']::varchar[], 'KE', 'Africa/Nairobi', NOW(), NOW()),
('a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'JOAT Demo Restaurant', 'joat-demo-restaurant', 'demo-restaurant.joat.com', 'restaurant', 'active', 'KES', ARRAY['mpesa']::varchar[], 'KE', 'Africa/Nairobi', NOW(), NOW());

-- Store Settings
INSERT INTO store_storesettings (id, store_id, low_stock_threshold, tagline, logo_url)
VALUES
('b1b2c3d4-e5f6-7890-abcd-ef1234567801', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 2, '', ''),
('b1b2c3d4-e5f6-7890-abcd-ef1234567802', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 3, '', '');

-- Store Themes
INSERT INTO store_storetheme (id, store_id, preset_slug, template_style)
VALUES
('c1b2c3d4-e5f6-7890-abcd-ef1234567801', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'bold', 'bold'),
('c1b2c3d4-e5f6-7890-abcd-ef1234567802', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'classic', 'classic');

-- Subscriptions (14 day trial)
INSERT INTO saas_storesubscription (store_id, plan_id, status, trial_ends_at, created_at, updated_at)
VALUES
('a1b2c3d4-e5f6-7890-abcd-ef1234567801', (SELECT id FROM saas_plan WHERE slug='starter'), 'trial', (NOW() + INTERVAL '14 days'), NOW(), NOW()),
('a1b2c3d4-e5f6-7890-abcd-ef1234567802', (SELECT id FROM saas_plan WHERE slug='pro'), 'trial', (NOW() + INTERVAL '14 days'), NOW(), NOW());

-- Platform Admin + Store Owners (password: Demo@1234)
-- Hash: pbkdf2_sha256$1000000$dVmoPrVV2lcUoFw7dr2GXG$oid9yxjK81oNPZyJx2za8DIMuSI5z95NBiMJatRqieA=
INSERT INTO users_user (password, is_superuser, first_name, last_name, is_staff, is_active, date_joined, email, role, store_id)
VALUES
('pbkdf2_sha256$1000000$dVmoPrVV2lcUoFw7dr2GXG$oid9yxjK81oNPZyJx2za8DIMuSI5z95NBiMJatRqieA=', TRUE, 'Platform', 'Admin', TRUE, TRUE, NOW(), 'admin@joat.com', 'platform_admin', NULL),
('pbkdf2_sha256$1000000$dVmoPrVV2lcUoFw7dr2GXG$oid9yxjK81oNPZyJx2za8DIMuSI5z95NBiMJatRqieA=', FALSE, 'Bar', 'Owner', FALSE, TRUE, NOW(), 'bar@joat.com', 'store_owner', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801'),
('pbkdf2_sha256$1000000$dVmoPrVV2lcUoFw7dr2GXG$oid9yxjK81oNPZyJx2za8DIMuSI5z95NBiMJatRqieA=', FALSE, 'Restaurant', 'Owner', FALSE, TRUE, NOW(), 'restaurant@joat.com', 'store_owner', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802');

-- ========================================
-- BAR MENU
-- ========================================

-- Bar Menu Sections
INSERT INTO restaurant_menusection (id, store_id, name, position) VALUES
('d1000000-e5f6-7890-abcd-ef1234567801', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Beers', 0),
('d1000000-e5f6-7890-abcd-ef1234567802', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Spirits', 1),
('d1000000-e5f6-7890-abcd-ef1234567803', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Wine', 2),
('d1000000-e5f6-7890-abcd-ef1234567804', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Cocktails', 3),
('d1000000-e5f6-7890-abcd-ef1234567805', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'Non-Alcoholic', 4);

-- Bar Menu Items
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_age_restricted, is_available, position) VALUES
('e1000000-e5f6-7890-abcd-ef1234567801', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567801', 'Tusker Lager', 250.00, TRUE, TRUE, 0),
('e1000000-e5f6-7890-abcd-ef1234567802', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567801', 'Guinness Stout', 300.00, TRUE, TRUE, 1),
('e1000000-e5f6-7890-abcd-ef1234567803', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567801', 'White Cap Lager', 280.00, TRUE, TRUE, 2),
('e1000000-e5f6-7890-abcd-ef1234567804', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567801', 'Heineken', 350.00, TRUE, TRUE, 3),
('e1000000-e5f6-7890-abcd-ef1234567805', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567802', 'Johnnie Walker Red', 500.00, TRUE, TRUE, 0),
('e1000000-e5f6-7890-abcd-ef1234567806', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567802', 'Jameson', 600.00, TRUE, TRUE, 1),
('e1000000-e5f6-7890-abcd-ef1234567807', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567802', 'Smirnoff Vodka', 450.00, TRUE, TRUE, 2),
('e1000000-e5f6-7890-abcd-ef1234567808', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567802', 'Bacardi Rum', 450.00, TRUE, TRUE, 3),
('e1000000-e5f6-7890-abcd-ef1234567809', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567803', 'House Red', 400.00, TRUE, TRUE, 0),
('e1000000-e5f6-7890-abcd-ef1234567810', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567803', 'House White', 400.00, TRUE, TRUE, 1),
('e1000000-e5f6-7890-abcd-ef1234567811', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567803', 'Sparkling', 500.00, TRUE, TRUE, 2),
('e1000000-e5f6-7890-abcd-ef1234567812', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567804', 'Mojito', 600.00, TRUE, TRUE, 0),
('e1000000-e5f6-7890-abcd-ef1234567813', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567804', 'Dawa', 500.00, TRUE, TRUE, 1),
('e1000000-e5f6-7890-abcd-ef1234567814', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567804', 'Gin & Tonic', 550.00, TRUE, TRUE, 2),
('e1000000-e5f6-7890-abcd-ef1234567815', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567805', 'Fresh Juice', 150.00, FALSE, TRUE, 0),
('e1000000-e5f6-7890-abcd-ef1234567816', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567805', 'Soda', 100.00, FALSE, TRUE, 1),
('e1000000-e5f6-7890-abcd-ef1234567817', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 'd1000000-e5f6-7890-abcd-ef1234567805', 'Red Bull', 200.00, FALSE, TRUE, 2);

-- Bar Tables
INSERT INTO restaurant_table (id, store_id, number, name, capacity, is_active) VALUES
('f1000000-e5f6-7890-abcd-ef1234567801', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 1, 'Window Seat', 2, TRUE),
('f1000000-e5f6-7890-abcd-ef1234567802', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 2, 'Corner Booth', 4, TRUE),
('f1000000-e5f6-7890-abcd-ef1234567803', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 3, 'Bar Counter', 6, TRUE),
('f1000000-e5f6-7890-abcd-ef1234567804', 'a1b2c3d4-e5f6-7890-abcd-ef1234567801', 4, 'VIP Lounge', 8, TRUE);

-- ========================================
-- RESTAURANT MENU
-- ========================================

-- Restaurant Menu Sections
INSERT INTO restaurant_menusection (id, store_id, name, position) VALUES
('d2000000-e5f6-7890-abcd-ef1234567801', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Starters', 0),
('d2000000-e5f6-7890-abcd-ef1234567802', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Mains', 1),
('d2000000-e5f6-7890-abcd-ef1234567803', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Pizzas', 2),
('d2000000-e5f6-7890-abcd-ef1234567804', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Drinks', 3),
('d2000000-e5f6-7890-abcd-ef1234567805', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'Desserts', 4);

-- Restaurant Menu Items
INSERT INTO restaurant_menuitem (id, store_id, section_id, name, price, is_available, position) VALUES
('e2000000-e5f6-7890-abcd-ef1234567801', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567801', 'Chicken Wings', 450.00, TRUE, 0),
('e2000000-e5f6-7890-abcd-ef1234567802', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567801', 'Samosas (3)', 200.00, TRUE, 1),
('e2000000-e5f6-7890-abcd-ef1234567803', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567801', 'Soup of the Day', 250.00, TRUE, 2),
('e2000000-e5f6-7890-abcd-ef1234567804', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567802', 'Nyama Choma', 800.00, TRUE, 0),
('e2000000-e5f6-7890-abcd-ef1234567805', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567802', 'Grilled Tilapia', 900.00, TRUE, 1),
('e2000000-e5f6-7890-abcd-ef1234567806', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567802', 'Biryani', 700.00, TRUE, 2),
('e2000000-e5f6-7890-abcd-ef1234567807', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567802', 'Beef Burger', 650.00, TRUE, 3),
('e2000000-e5f6-7890-abcd-ef1234567808', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567802', 'Vegetable Stir Fry', 500.00, TRUE, 4),
('e2000000-e5f6-7890-abcd-ef1234567809', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567803', 'Margherita', 600.00, TRUE, 0),
('e2000000-e5f6-7890-abcd-ef1234567810', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567803', 'BBQ Chicken', 750.00, TRUE, 1),
('e2000000-e5f6-7890-abcd-ef1234567811', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567803', 'Pepperoni', 700.00, TRUE, 2),
('e2000000-e5f6-7890-abcd-ef1234567812', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567804', 'Fresh Juice', 150.00, TRUE, 0),
('e2000000-e5f6-7890-abcd-ef1234567813', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567804', 'Soda', 100.00, TRUE, 1),
('e2000000-e5f6-7890-abcd-ef1234567814', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567804', 'Water', 50.00, TRUE, 2),
('e2000000-e5f6-7890-abcd-ef1234567815', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567804', 'Chai', 80.00, TRUE, 3),
('e2000000-e5f6-7890-abcd-ef1234567816', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567805', 'Chocolate Lava Cake', 400.00, TRUE, 0),
('e2000000-e5f6-7890-abcd-ef1234567817', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 'd2000000-e5f6-7890-abcd-ef1234567805', 'Fruit Salad', 250.00, TRUE, 1);

-- Restaurant Tables
INSERT INTO restaurant_table (id, store_id, number, name, capacity, is_active) VALUES
('f2000000-e5f6-7890-abcd-ef1234567801', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 1, 'Table 1', 2, TRUE),
('f2000000-e5f6-7890-abcd-ef1234567802', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 2, 'Table 2', 4, TRUE),
('f2000000-e5f6-7890-abcd-ef1234567803', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 3, 'Table 3', 4, TRUE),
('f2000000-e5f6-7890-abcd-ef1234567804', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 4, 'Terrace 1', 6, TRUE),
('f2000000-e5f6-7890-abcd-ef1234567805', 'a1b2c3d4-e5f6-7890-abcd-ef1234567802', 5, 'Terrace 2', 8, TRUE);

SELECT 'Seed data inserted successfully!' AS status;
