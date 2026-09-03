# Addendum: Technical Decisions & Architecture Notes

## Architecture Decisions (from party session)

### A1: Tenant Isolation — X-Store-ID Header
**Decision:** X-Store-ID header accepted only for `platform_admin` role. Store users resolve tenant exclusively from JWT `store_id` claim.
**Rationale:** Option 1 (remove header) breaks storefront. Option 2 (validate against JWT) adds latency and confused-deputy risk. Option 3 is correct because platform admins need cross-tenant visibility while store users are bound to single store.
**Implementation:** Modify `TenantMiddleware.process_request` to check JWT role after UUID lookup. Add 403 rejection for non-admin with X-Store-ID.

### A2: Celery Worker Reliability
**Decision:** Uncomment worker in render.yaml, add heartbeat monitoring.
**Rationale:** Worker is dead — notifications, inventory alerts, payment reconciliation are all silent failures. "Phantom payments" where customer charged but order shows unpaid.
**Implementation:** Add worker service to render.yaml. Add `/api/v1/health/celery/` endpoint with `celery_app.control.ping()`. Add Celery task that checks `inspect.active()` every 60s, fires alert if zero workers.

### A3: Cold Boot Mitigation
**Decision:** Add cron ping every 10min to keep Render web service alive.
**Rationale:** Render free tier sleeps after 15min idle. Payments confirmed during sleep get lost unless webhook retries.
**Implementation:** cron-job.org hitting `/api/v1/health/` every 10min.

### A4: M-Pesa Callback Security
**Decision:** Make `MPESA_WEBHOOK_SECRET` required in production. Raise `ImproperlyConfigured` if missing.
**Rationale:** Currently defaults to empty string, silently disabling verification. Attackers could flood endpoint with invalid signatures.
**Implementation:** Add validation in `production.py` similar to `STRIPE_SECRET_KEY` pattern.

### A5: Subscription Billing Architecture
**Decision:** Add `billing.renewals` Celery Beat task (daily, 2am EAT) that checks subscriptions where `current_period_end <= now()`. Charge stored M-Pesa payment method or suspend after 7-day grace period.
**Rationale:** No recurring billing flow exists. Store owners could use platform free forever.
**Implementation:** New Celery task, M-Pesa STK Push for renewals, suspension logic.

### A6: EOD Reconciliation
**Decision:** Raw SQL query for v1, no BarDailyReconciliation model yet.
**Rationale:** Premature optimization. 100 orders/day × 3KB = ~27MB after 90 days. Don't build retention policy before retention problem.
**Implementation:** API endpoint running `GROUP BY date, payment_method` on Order table. Upgrade to model when query performance hurts (month 3-6).

### A7: Data Retention
**Decision:** Keep detailed orders 12 months (KRA audit), aggregate into DailyRevenueSummary, hard-delete originals.
**Rationale:** Supabase 500MB limit. ~110MB for raw orders after 3 years. Add/TabRound/TabItem = 300-400MB.
**Implementation:** Monthly Celery task `archive_old_orders`: run summary backfill, hard-delete Orders >90 days with confirmed summary.

### A8: WhatsApp Daily Summary
**Decision:** Celery Beat task at 22:00 EAT sends summary via Twilio. SMS backup for feature phones via Africa's Talking API.
**Rationale:** Bar owners check WhatsApp 50x/day, email once a week. SMS covers long tail of feature phone users.
**Implementation:** `analytics.tasks.daily_summary` formats and sends. No new UI, just automated messages.

### A9: Performance — N+1 Fixes
**Decision:** Add `select_related("payment_transaction")` to Order queries. Pre-compute Tab.total_amount on model. Add composite index: `(store_id, status, confirmed_at) INCLUDE (total_amount)`.
**Rationale:** Admin dashboard "recent orders" will N+1 on Order.payment_transaction FK. Tab.total_amount property computes by summing all items on each call.
**Implementation:** QuerySet optimization, model field update, migration for index.

### A10: Connection Pooling
**Decision:** Set `CONN_MAX_AWS=4` with PgBouncer pool_size=10 on Supabase, `pool_timeout=10`.
**Rationale:** Render free tier has 1 connection limit. 2 gunicorn workers + 1 Celery worker = 3 connections. At 10 concurrent admin users, connections exhausted.
**Implementation:** Update Django settings, configure Supabase PgBouncer.

## Market Intelligence (from Mary)

### Revenue Projections (Year 1, 10 Bar Clients)
| Scenario | Free | Starter | Growth | Pro | Monthly MRR | Annual ARR |
|----------|------|---------|--------|-----|-------------|------------|
| Conservative | 4 | 4 | 2 | 0 | KES 25,000 | KES 300,000 |
| Moderate | 2 | 4 | 3 | 1 | KES 67,500 | KES 810,000 |
| Optimistic | 1 | 3 | 4 | 2 | KES 105,000 | KES 1,260,000 |

**Realistic Year 1: KES 500,000–800,000 (~$3,800–6,100 USD)**

### Competitive Position
- **Kenya-first M-Pesa integration** — no card reader dependency
- **WhatsApp summaries** — owners get insights where they communicate
- **Pre-loaded bar templates** — onboarding in minutes vs hours
- **Tab-first workflow** — designed for bar-specific pain points

### Business Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| M-Pesa API downtime | Critical | Always-on cash fallback |
| Free tier abuse | High | 100-txn hard cap |
| Single client dependency | High | Diversify to 3+ verticals in 6 months |
| Owner doesn't adopt summaries | Medium | Auto-send + training during onboarding |

## Deployment Checklist (from Winston)

### Pre-Launch
- [ ] Uncomment Celery worker in render.yaml
- [ ] Add cron-job.org ping every 10min
- [ ] Fix X-Store-ID vulnerability
- [ ] Make MPESA_WEBHOOK_SECRET required in production
- [ ] Add Sentry DJS to backend + Next.js frontends
- [ ] Add UptimeRobot health check every 5min
- [ ] Verify cross-tenant isolation tests pass
- [ ] Run `check --deploy` in build phase

### Week 3-4
- [ ] Celery worker health monitoring
- [ ] Subscription billing enforcement
- [ ] WhatsApp daily summary (Twilio)
- [ ] Tenant isolation audit
- [ ] Payment reconciliation hardening

### Month 2-3
- [ ] WhatsApp as storefront (Meta Cloud API)
- [ ] Real-time order tracking
- [ ] Inventory alerts
- [ ] Multi-store analytics
- [ ] Subscription self-serve

## Alternatives Considered (from Wildcard)

1. **WhatsApp as storefront** — Skip custom PWA, use WhatsApp Business API for ordering. 15M+ WhatsApp users in Kenya. Deferred to month 2-3 due to Meta Cloud API complexity.
2. **USSD ordering** — *123# menu for feature phones. Deferred to v3 due to Africa's Talking integration complexity.
3. **Offline-first SQLite** — For bars with bad connectivity. Deferred to v3 due to sync complexity.
4. **Kiosk mode** — Staff tablet for order taking. Deferred to v2.
5. **Perishable inventory with time-based pricing** — Drinks at 6pm worth more than 2am. Deferred to v2.
