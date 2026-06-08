# JOAT Stores — Sales & Commercial Strategy for Kenyan SMEs

This document details the sales strategy, product packaging, and customer acquisition playbook to launch and sell JOAT Stores to local Kenyan businesses.

---

## 1. The Value Proposition for Kenyan SMEs

Small and medium-sized businesses in Kenya face massive fees from global tech providers and delivery apps:
- **Delivery Apps (UberEats, Glovo, Bolt Food)** charge **25% to 30% commission** on every order, which wipes out the margins of local fast-food cafes, butcheries, and pubs.
- **Shopify & Wix** require USD credit card billing, have no built-in M-Pesa integration, and are complex for merchants who only use mobile phones.
- **Custom Web Developers** charge KES 50,000+ upfront with long delivery times and high maintenance costs.

**The JOAT Stores Pitch**:
> "Get a professional, custom-branded website with automatic M-Pesa payments and WhatsApp ordering notifications for less than the price of a cup of coffee per day. Keep 100% of your sales."

---

## 2. SME Plan Packaging

We organize the market into four specific tiers to simplify the sales process:

### Tier 1: The Trial Shop
- **Target**: Curious owners testing the waters.
- **Price**: KES 0 (14 days).
- **Features**: Subdomain (e.g., `shopname.joatstores.com`), maximum 15 products, basic shop interface, email notifications.
- **Call-to-Action**: Prompt upgrade once they reach 10 orders.

### Tier 2: JOAT Starter (KES 1,500 / month)
- **Target**: Small retail kiosks, clothing boutiques, and electronics shops (Dukas).
- **Price**: KES 1,500/month (billed via M-Pesa STK Push).
- **Limits**: 100 products, 500 orders/month, 2 staff accounts.
- **Features**: M-Pesa STK checkout, basic storefront styling, custom branding.

### Tier 3: JOAT Growth (KES 3,500 / month)
- **Target**: Local restaurants, fast-food joints, cafes, pubs, and bars.
- **Price**: KES 3,500/month.
- **Limits**: 1,000 products, unlimited orders, 5 staff accounts.
- **Features**:
  - **Table QR-Code Ordering**: Diners scan a QR code at their table to view the menu and pay immediately via M-Pesa.
  - **Menu Builder**: Setup modifier items (e.g., "Add extra cheese," "Well done").
  - **WhatsApp Notifications**: Real-time order confirmations sent directly to the customer and the shop manager.

### Tier 4: JOAT Pro (KES 8,000 / month)
- **Target**: Multi-branch restaurants or high-volume wholesale/retail businesses.
- **Price**: KES 8,000/month.
- **Limits**: Unlimited products, unlimited orders, unlimited staff.
- **Features**: Custom domain connection, analytics dashboard, AI-driven cross-selling recommendations.

---

## 3. The 30-Day Go-To-Market Playbook

### Week 1: Nairobi Pilot (Direct Sales)
- Select **10 friendly local businesses** (specifically restaurants/pubs in Nairobi neighborhoods like Kilimani, Westlands, or CBD).
- Build their digital stores *for them* in under 10 minutes using their Instagram/Facebook photos.
- Visit the business in person, print a mock table QR stand, place it on a table, and show the owner: *"Scan this with your phone. Look, your menu is online, and customers can order instantly."*
- Offer a **30-day extended free trial** for the pilot group in exchange for video testimonials.

### Week 2: Social Media & WhatsApp Funnels
- Set up a simple landing page highlighting: **"Tired of 30% Commissions?"**
- Run targeted Facebook/Instagram ads aimed at "Business Owners in Kenya" with a clear CTA: *"Create your store in 5 minutes. No credit card required."*
- Connect a WhatsApp Business account where owners can text "START" to automatically launch a basic storefront via a quick onboarding bot.

### Week 3: Merchant Referral Program
- Introduce a referral dashboard.
- Every merchant gets a referral link. If a referred store pays for their first month, the referrer gets **KES 500 credit** on their next bill. This leverages the close-knit Kenyan merchant networks.

---

## 4. Billing & Cash Flow Management

- **Local Collection**: Standard SaaS card billing (Stripe) has low adoption in Kenya. All subscription payments must flow through **M-Pesa STK Push** or **C2B Paybill**.
- **Automated Suspension**:
  - Subscription cycles run for 30 days.
  - On Day 27, Celery sends a WhatsApp payment reminder.
  - On Day 30, the system triggers an STK push to the registered merchant's Safaricom number.
  - If unpaid by Day 32, the store transitions to `suspended`. The customer storefront automatically displays: *"This store is temporarily offline. Please contact the administrator."*
