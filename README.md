# joat_stores

> **A multi-tenant, AI-augmented, headless commerce operating system designed to empower African SMEs with scalable digital retail infrastructure.**

---

## What This Is

joat_stores is not a store builder. It is **commerce infrastructure** — a self-hosted, multi-tenant headless commerce engine that lets African SMEs launch branded online stores, accept local payments, manage their business, and grow with analytics-driven intelligence.

Built for Kenyan merchants first. Designed to scale across Africa.

This is the platform Instagram sellers, TikTok sellers, fashion retailers, electronics shops, and physical-to-digital businesses never had — affordable, locally-optimized, and owned outright.

---

## Why It Exists

| The Problem | The Reality |
|---|---|
| Shopify pricing | $79–$299/month per store — unviable for African SMEs |
| WooCommerce | Too technical, no multi-tenancy, no headless-first design |
| Instagram DMs + WhatsApp | No inventory, no analytics, no real checkout |
| Custom builds | Months of engineering, no scaling path, no shared infra |
| Payment integrations | M-Pesa is an afterthought on Western platforms |

joat_stores solves all five simultaneously.

---

## Core Identity

One Django backend powers N independent storefronts via domain-based tenant resolution. Each store is fully isolated at the query, auth, and data levels. Next.js frontends are independently deployable per brand. The platform runs on your own infrastructure — zero per-store SaaS fees, zero vendor lock-in.

```
[techstore.joat.com]   [fashionstore.joat.com]   [merchant3.com]   ...N stores
        ↓                        ↓                        ↓
  ███████████████████████████████████████████████████████████████
  █              joat_stores API (Django + DRF)                  █
  █  Tenant Resolver → Auth → Commerce → Analytics → AI         █
  ███████████████████████████████████████████████████████████████
        ↓                        ↓                        ↓
  [PostgreSQL]              [Redis]               [Celery]
```

---

## Feature Overview

### 🏗 Multi-Tenant Platform Core

- Domain-based store resolution middleware
- Full tenant isolation at queryset, serializer, and permission layers
- No cross-tenant data access — enforced at every layer
- Store configuration and theme customization per tenant
- Feature flags tied to subscription plan
- Subscription tier enforcement (Basic / Growth / Pro)
- Platform Admin panel with full multi-store visibility

### 🛒 Commerce Engine

**Products**
- Product catalog with categories, attributes, and variants
- Dynamic attribute system (size, color, material — per store)
- SKU management and inventory tracking
- Media management (images per variant)
- Soft delete system with audit fields

**Orders**
- Full order lifecycle: created → confirmed → fulfilled → completed
- Status transitions with timestamps
- Payment confirmation hooks
- Refund handling
- Delivery tracking integration-ready

**Cart**
- Store-isolated, Redis-backed persistent cart
- Guest cart and authenticated cart merge
- Coupon and discount support
- Abandoned cart tracking

### 💳 Payments

- **M-Pesa integration** (primary — STK Push, C2B, B2C)
- Card payments (provider-agnostic scaffold)
- Webhook verification and idempotency
- Payment records with provider reference tracking
- Fraud detection logic scaffold
- *Future:* Wallet system, store credit, split payments

### 👥 Users & Roles

| Role | Scope |
|---|---|
| Platform Admin | Full platform — all stores, all tenants |
| Store Owner | Single store — full access |
| Store Manager | Single store — operational access |
| Customer | Store-scoped — own orders and profile |

- JWT authentication (short-lived access + refresh tokens)
- Object-level permission enforcement
- Feature access gated per subscription plan

### 📊 Analytics Engine (Core Differentiator)

**Store-Level Analytics**

| Category | Metrics |
|---|---|
| Sales | Revenue (daily/weekly/monthly), trend graph, AOV, top products, top categories |
| Customers | Growth rate, LTV, purchase frequency, geographic distribution, repeat rate |
| Products | Best sellers, underperforming products, low stock alerts, inventory turnover |
| Conversion | Cart abandonment rate, checkout completion rate, payment success rate |

**Platform-Level Analytics (SaaS Admin)**

- Total stores and active subscriptions
- MRR (Monthly Recurring Revenue)
- Platform GMV (Gross Merchandise Volume)
- Store churn rate
- Revenue per subscription tier
- Feature usage tracking

### 🤖 AI Engine (Architecture-Ready)

The AI module is scaffolded from day one — no logic at MVP, full extension surface for Phase 3.

| Module | Capability |
|---|---|
| Recommendation Engine | Collaborative filtering, "customers also bought," cross-sell |
| Dynamic Pricing | Sales velocity-based pricing suggestions, demand forecasting |
| Inventory Forecasting | Predict stock-outs, suggest reorder quantities |
| Customer Segmentation | High-value, at-risk churn, discount-sensitive buyer segments |

### ⚡ Async & Background Jobs (Celery + Redis)

- Order confirmation emails
- Low-stock alert detection and supplier notifications
- Inventory sync tasks
- Scheduled reporting
- Dead-letter queue + retry logic
- Worker health monitoring

### 🔒 Security

- JWT + httpOnly secure cookies
- Role-based access control (RBAC) with store-scoped enforcement
- Request throttling and rate limiting
- CORS restrictions with domain whitelist
- Encrypted secrets via environment variables
- Structured audit logging on all business models

### 🏪 Supplier Communication Module

- Supplier model with contact and product line linkage
- Inventory alert thresholds per product per store
- Automatic low-stock detection via Celery Beat
- Supplier notification emails (async)
- Restock request records with status tracking

### 🐳 Infrastructure

- Docker Compose (backend, redis, celery, celery-beat, storefronts)
- Internal Docker network — no external port exposure except Nginx proxy
- Nginx reverse proxy with per-store domain config
- Zero conflict with existing VPS services
- Non-root containers, environment variable validation on startup
- PostgreSQL on isolated database (separate from existing services)
- Volume management for DB data, media, and static files
- Health check endpoint (`/health/`)
- Gunicorn with production Django settings

---

## SaaS Monetization

| Plan | Products | Staff | Analytics | AI | Price |
|---|---|---|---|---|---|
| Basic | 50 | 1 | Basic | — | Affordable |
| Growth | 500 | 5 | Advanced | — | Mid-tier |
| Pro | Unlimited | Unlimited | Full | ✓ | Premium |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Django 5.2 LTS + Django REST Framework |
| Frontend | Next.js 16.x App Router (TypeScript strict) |
| Database | PostgreSQL 17.x |
| Cache / Sessions | Redis 8.6 |
| Async Jobs | Celery 5.6.2 + Celery Beat |
| Proxy | Nginx |
| Containerization | Docker + Docker Compose |
| Auth | JWT (simplejwt + custom store_id claim) |
| Payments | M-Pesa (Daraja API), card scaffold |

---

## 12-Month Roadmap

**Phase 1 — MVP (Month 1–3)**
- Multi-store engine live with 2+ tenant storefronts
- M-Pesa payments operational (retail + F&B)
- Basic analytics dashboard
- Restaurant dine-in + bar tab live
- Platform admin operational
- Third tenant onboarded in < 24 hours (investor demo)

**Phase 2 — SaaS (Month 4–6)**
- Live SaaS billing via M-Pesa
- Advanced analytics dashboard
- AI recommendation engine (first model)
- Merchant self-service onboarding portal
- SSE real-time kitchen updates

**Phase 3 — Scale (Month 7–12)**
- Marketplace features
- Vendor onboarding flow
- POS integration
- 5+ active merchant tenants
- Investor-facing metrics dashboard
- Full AI engine (dynamic pricing, forecasting, segmentation)

---

## Target Market

Kenyan SMEs ready to move from Instagram DMs and WhatsApp orders to real, owned, analytics-driven digital commerce:

- Fashion retailers and clothing boutiques
- Electronics and accessories sellers
- Instagram / TikTok sellers going multi-channel
- Physical shops transitioning online
- Portfolio operators running multiple brands
- Restaurants and bars replacing manual operations with digital infrastructure

---

## Strategic Goal

Build the **Kenyan-first multi-vertical commerce operating system** — retail, restaurants, and bars on a single platform — optimized for local payments, mobile-first UX, African-market pricing, and AI-powered growth intelligence.

Not just stores. Infrastructure.

---

## Project Development Progress

> **Status:** Pre-implementation planning **complete**. Implementation readiness verified. **Ready for Sprint 1.**

### Phase 0 — Planning & Architecture

| Artifact | Status | Location |
|---|---|---|
| Product Brief | ✅ Complete | `_bmad-output/planning-artifacts/product-brief-joat_stores-2026-02-23.md` |
| Product Requirements Document (PRD) | ✅ Complete | `_bmad-output/planning-artifacts/prd.md` |
| Architecture Decision Document | ✅ Complete | `_bmad-output/planning-artifacts/architecture.md` |
| UX Design Specification | ✅ Complete | `_bmad-output/planning-artifacts/ux-design-specification.md` |
| Epics & User Stories | ✅ Complete | `_bmad-output/planning-artifacts/epics.md` |
| Project Context for AI Agents | ✅ Complete | `_bmad-output/project-context.md` |
| Implementation Readiness Report | ✅ Complete — READY | `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-03.md` |

**Planning scope:** 101 functional requirements, 22 non-functional requirements, 83 user stories across 12 epics, 7 user journeys.

### Epic Structure (83 Stories)

| Epic | Scope | Stories |
|---|---|---|
| Epic 1 | Multi-Tenant Platform Foundation + Auth | 9 |
| Epic 2 | Multi-Provider Payments Engine (M-Pesa) | 7 |
| Epic 3 | Restaurant Full-Service | 13 |
| Epic 4 | Retail Store Commerce | 10 |
| Epic 5 | Bar Tab Management | 5 |
| Epic 6 | Contracting Module | 6 |
| Epic 7 | Reliable Async Operations (Celery) | 4 |
| Epic 8 | Merchant Analytics Dashboard | 7 |
| Epic 9 | SaaS Plans + Subscription Management | 7 |
| Epic 10 | Customer Loyalty + Engagement | 6 |
| Epic 11 | AI + Personalization | 3 |
| Epic 12 | Production Hardening | 6 |

### Architecture Decisions Locked

| Decision | Choice |
|---|---|
| Backend | Django 5.2 LTS + DRF + Python 3.14.3 |
| Frontend | Next.js 16.x App Router (TypeScript strict) |
| Multi-tenancy | Shared DB, shared schema — store_id FK isolation at 5 layers |
| Payments | M-Pesa Daraja STK Push (primary rail across all verticals) |
| Auth | djangorestframework-simplejwt + custom store_id JWT claim |
| Async | Celery 5.6.2 + Redis 8.6 + DLQ from day one |
| Deployment | Docker Compose on VPS — no Kubernetes at MVP |
| CI/CD | GitHub Actions — lint + test + SSH deploy on merge to main |

### Implementation Sequence

- [x] Product Brief
- [x] Market & domain research
- [x] PRD (101 FRs, 22 NFRs)
- [x] UX Design Specification
- [x] Architecture
- [x] Epics & Stories (83 stories, 12 epics)
- [x] Implementation readiness verification
- [ ] **Sprint 1 — Epic 1:** Monorepo scaffold (cookiecutter-django + Next.js apps + Docker Compose)
- [ ] **Sprint 1 — Epic 1:** Tenant foundation — TenantModel, TenantMiddleware, JWT + RBAC
- [ ] **Epic 2:** M-Pesa integration — STK Push, webhook verification, reconciliation
- [ ] **Epic 3:** Restaurant module — menu, QR dine-in, table session, kitchen view
- [ ] **Epic 4:** Retail module — product catalog, cart, orders, checkout
- [ ] **Epic 5:** Bar module — tab, rounds, happy hour, age restriction
- [ ] **Epic 8:** Analytics dashboard — pre-aggregated revenue + order summaries
- [ ] **Epic 9:** SaaS billing — subscription plans + M-Pesa recurring payments
- [ ] **Epic 11:** AI engine — recommendations, dynamic pricing, inventory forecasting
- [ ] **Epic 12:** Production hardening — CI/CD, monitoring, Kenya DPA compliance

---

*Built by KAFURAHA — joat_stores © 2026*
