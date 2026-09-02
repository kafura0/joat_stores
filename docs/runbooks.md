# JOAT Stores — Operational Runbooks

## Table of Contents

1. [Merchant Onboarding](#1-merchant-onboarding)
2. [Database Backup & Recovery](#2-database-backup--recovery)
3. [M-Pesa Credential Swap](#3-m-pesa-credential-swap)
4. [Subscription Suspension](#4-subscription-suspension)
5. [Payment Reconciliation](#5-payment-reconciliation)
6. [PII Anonymisation](#6-pii-anonymisation)
7. [Celery Worker Recovery](#7-celery-worker-recovery)
8. [SSL Certificate Renewal](#8-ssl-certificate-renewal)
9. [Store Status Management](#9-store-status-management)
10. [Emergency Procedures](#10-emergency-procedures)

---

## 1. Merchant Onboarding

**Target:** Complete in under 24 hours (core investor thesis metric)

### Prerequisites
- Domain DNS configured (TTL ≤ 300s)
- Store owner email verified
- Subscription payment confirmed

### Steps

```bash
# 1. Provision store via API
curl -X POST https://api.joatstores.com/api/v1/platform/stores/ \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Store",
    "slug": "new-store",
    "domain": "new-store.joatstores.com",
    "tenant_type": "restaurant",
    "currency": "KES",
    "country": "KE",
    "timezone": "Africa/Nairobi",
    "payment_methods": ["mpesa"],
    "owner_email": "owner@example.com"
  }'

# 2. Verify store resolves
curl -I https://new-store.joatstores.com/
# Expected: HTTP 200

# 3. Verify owner JWT contains correct store_id
curl -X POST https://api.joatstores.com/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "owner@example.com", "password": "<temp_password>", "store_slug": "new-store"}'
# Check JWT payload for store_id

# 4. Verify empty product list
curl https://api.joatstores.com/api/v1/store/products/ \
  -H "Authorization: Bearer <owner_token>"
# Expected: {"data": [], "meta": {"count": 0, ...}}

# 5. Add Nginx config for new tenant
# (Manual step at MVP)
cat > nginx/conf.d/tenants/new-store.conf << 'EOF'
server {
    listen 80;
    server_name new-store.joatstores.com;
    location / {
        proxy_pass http://storefront:3000;
        proxy_set_header Host $host;
    }
}
EOF

# 6. Reload Nginx
docker compose exec nginx nginx -s reload
```

### Verification Checklist
- [ ] Store resolves at domain
- [ ] Owner JWT contains correct `store_id`
- [ ] `GET /api/v1/products/` returns empty list (not 403)
- [ ] Owner can access admin dashboard
- [ ] Subscription status is `trial`

---

## 2. Database Backup & Recovery

### Automated Backups

Backups run daily via Celery Beat at 00:00 UTC:
- Command: `pg_dump | gzip`
- Location: `/backups/YYYY-MM-DD.sql.gz`
- Retention: 7 days

### Manual Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U postgres joat_stores | gzip > backup_$(date +%Y%m%d).sql.gz

# List backups
ls -la /backups/*.sql.gz
```

### Recovery

```bash
# Stop Django and Celery
docker compose stop django celery celery-beat

# Restore database
gunzip < /backups/20260301.sql.gz | docker compose exec -T postgres psql -U postgres joat_stores

# Run migrations
docker compose exec django python manage.py migrate

# Restart services
docker compose up -d
```

### Verification

```bash
# Check database
docker compose exec django python manage.py shell -c "
from apps.store.models import Store
print(f'Stores: {Store.objects.count()}')
from apps.order.models import Order
print(f'Orders: {Order.objects.count()}')
"
```

---

## 3. M-Pesa Credential Swap

### Sandbox → Production

```bash
# 1. Update environment variables in .env
MPESA_CONSUMER_KEY=your_production_key
MPESA_CONSUMER_SECRET=your_production_secret
MPESA_SHORTCODE=your_production_shortcode
MPESA_PASSKEY=your_production_passkey
MPESA_CALLBACK_URL=https://api.joatstores.com/api/v1/payments/mpesa-callback/

# 2. Restart services
docker compose restart django celery celery-beat

# 3. Verify health endpoint
curl https://api.joatstores.com/api/v1/payments/mpesa-status/
# Expected: {"status": "healthy", "environment": "production"}

# 4. Test with small amount
curl -X POST https://api.joatstores.com/api/v1/payments/initiate-stk/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+254712345678", "amount": "1.00", "reference": "test-swap"}'
```

### Verification Checklist
- [ ] `/api/v1/payments/mpesa-status/` returns `environment: production`
- [ ] Test STK Push succeeds with production credentials
- [ ] Webhook callback received and processed
- [ ] No errors in Celery logs

---

## 4. Subscription Suspension

### Automated Process

Runs daily at 01:00 UTC via `suspend_past_due_subscriptions`:

1. Scans subscriptions with `status=past_due` and `past_due_since < 7 days ago`
2. Transitions status to `suspended`
3. Store frontend displays: "This store is temporarily offline"
4. Store API returns 503 for all endpoints

### Manual Suspension

```bash
# Suspend a specific store
curl -X PATCH https://api.joatstores.com/api/v1/platform/subscriptions/{id}/ \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "suspended"}'
```

### Reactivation

```bash
# Reactivate after payment
curl -X PATCH https://api.joatstores.com/api/v1/platform/subscriptions/{id}/ \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "active", "period_start": "2026-03-01", "period_end": "2026-03-31"}'
```

---

## 5. Payment Reconciliation

### Automated Process

Runs daily at 00:30 UTC via `reconcile_payments`:

1. Finds `STK_PUSH_INITIATED` payments older than 2 hours
2. Queries Daraja Transaction Status API
3. Updates status to CONFIRMED/EXPIRED/FAILED

### Manual Reconciliation

```bash
# Trigger manual reconciliation
docker compose exec django python manage.py shell -c "
from apps.payment.tasks import reconcile_payments
reconcile_payments.apply()
"

# Check specific payment
docker compose exec django python manage.py shell -c "
from apps.payment.models import MpesaTransaction
tx = MpesaTransaction.objects.get(reference='your-reference')
print(f'Status: {tx.status}')
print(f'Receipt: {tx.mpesa_receipt_number}')
"
```

### STK Push Timeout Handling

- Timeout after ~30s → `ResultCode: 1032` (cancelled) or `1037` (timeout)
- Payment status set to `EXPIRED` (never `FAILED`)
- Order stays `PENDING`
- Customer sees retry prompt

```bash
# Check expired payments
docker compose exec django python manage.py shell -c "
from apps.payment.models import MpesaTransaction
expired = MpesaTransaction.objects.filter(status='EXPIRED').count()
print(f'Expired payments: {expired}')
"
```

---

## 6. PII Anonymisation

### Automated Process

Runs daily at 02:00 UTC via `anonymise_cancelled_store_pii`:

1. Scans orders for stores cancelled 30+ days ago
2. Anonymises PII fields:
   - `customer_phone` → hashed
   - `customer_name` → 'ANONYMISED'
   - `customer_email` → hashed

### Manual Anonymisation

```bash
# Anonymise specific store
docker compose exec django python manage.py shell -c "
from apps.saas.tasks import anonymise_cancelled_store_pii
anonymise_cancelled_store_pii.apply(args=[store_id])
"

# Verify anonymisation
docker compose exec django python manage.py shell -c "
from apps.order.models import Order
from apps.store.models import Store
store = Store.objects.get(slug='cancelled-store')
orders = Order.objects.filter(store=store)[:5]
for order in orders:
    print(f'Phone: {order.customer_phone}, Name: {order.customer_name}')
"
```

---

## 7. Celery Worker Recovery

### Check Worker Status

```bash
# Check worker health
curl https://api.joatstores.com/api/v1/health/workers/
# Expected: {"status": "healthy", "workers": [...]}

# Check Celery Flower
curl https://api.joatstores.com:5555/api/workers
```

### Restart Worker

```bash
# Restart Celery worker
docker compose restart celery

# Check logs
docker compose logs -f celery
```

### Dead Letter Queue (DLQ)

```bash
# Check DLQ contents
docker compose exec redis redis-cli ZRANGE celery:dlq 0 -1 WITHSCORES

# Clear DLQ
docker compose exec redis redis-cli DEL celery:dlq
```

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Worker not processing | Tasks stuck in queue | `docker compose restart celery` |
| DLQ filling up | Failed tasks accumulating | Check task logic, fix bug, clear DLQ |
| Worker heartbeat timeout | 503 on `/health/workers/` | `docker compose restart celery` |
| Beat schedule not running | Scheduled tasks not executing | `docker compose restart celery-beat` |

---

## 8. SSL Certificate Renewal

### Let's Encrypt (Production)

```bash
# Check certificate expiry
openssl x509 -enddate -noout -in /etc/letsencrypt/live/joatstores.com/cert.pem

# Renew certificate
certbot renew

# Reload Nginx
docker compose exec nginx nginx -s reload
```

### Verify SSL

```bash
# Check SSL certificate
curl -I https://api.joatstores.com/
# Expected: HTTP/2 200, strict-transport-security header
```

---

## 9. Store Status Management

### Status Transitions

```
pending → active (after onboarding complete)
active → suspended (subscription past due 7+ days)
suspended → active (payment received)
suspended → cancelled (merchant request or 30+ days suspended)
cancelled → terminal (no further transitions)
```

### Manual Status Update

```bash
# Suspend store
curl -X PATCH https://api.joatstores.com/api/v1/platform/stores/{id}/status/ \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "suspended"}'

# Reactivate store
curl -X PATCH https://api.joatstores.com/api/v1/platform/stores/{id}/status/ \
  -H "Authorization: Bearer <platform_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

### Status Effects

| Status | Storefront | API | Admin |
|--------|------------|-----|-------|
| `pending` | 503 | 503 | Accessible |
| `active` | Normal | Normal | Accessible |
| `suspended` | 503 | 503 | Accessible |
| `cancelled` | 404 | 404 | Read-only |

---

## 10. Emergency Procedures

### Database Connection Lost

```bash
# Check PostgreSQL status
docker compose exec postgres pg_isready

# Restart PostgreSQL
docker compose restart postgres

# Check connection from Django
docker compose exec django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('Database connection OK')
"
```

### Redis Connection Lost

```bash
# Check Redis status
docker compose exec redis redis-cli ping

# Restart Redis
docker compose restart redis

# Check connection from Django
docker compose exec django python manage.py shell -c "
from django.core.cache import cache
cache.set('test', 'ok', 10)
print(cache.get('test'))
"
```

### M-Pesa Service Down

```bash
# Check Daraja health
curl https://api.joatstores.com/api/v1/payments/mpesa-status/

# Check recent failed payments
docker compose exec django python manage.py shell -c "
from apps.payment.models import MpesaTransaction
recent = MpesaTransaction.objects.filter(
    status='FAILED',
    initiated_at__gte=timezone.now() - timedelta(hours=1)
).count()
print(f'Failed payments (last hour): {recent}')
"
```

### Full System Recovery

```bash
# 1. Stop all services
docker compose down

# 2. Start infrastructure
docker compose up -d postgres redis

# 3. Wait for database
docker compose exec postgres pg_isready

# 4. Run migrations
docker compose exec django python manage.py migrate

# 5. Start application
docker compose up -d

# 6. Verify health
curl https://api.joatstores.com/health/
curl https://api.joatstores.com/api/v1/health/workers/
```

### Contact Escalation

| Issue | Contact | SLA |
|-------|---------|-----|
| Database outage | Supabase support | 4 hours |
| Redis outage | Upstash support | 4 hours |
| M-Pesa issues | Safaricom Daraja support | 24 hours |
| VPS issues | Render support | 24 hours |
| DNS issues | Domain registrar | 24 hours |

---

## Appendix: Useful Commands

```bash
# Docker
docker compose ps                    # Service status
docker compose logs -f <service>     # Follow logs
docker compose exec <service> sh     # Shell into container

# Django
docker compose exec django python manage.py shell_plus
docker compose exec django python manage.py dbshell
docker compose exec django python manage.py test

# Celery
docker compose exec django celery -A config.celery_app inspect active
docker compose exec django celery -A config.celery_app inspect stats

# Redis
docker compose exec redis redis-cli
docker compose exec redis redis-cli KEYS "*"

# PostgreSQL
docker compose exec postgres psql -U postgres joat_stores
docker compose exec postgres pg_dump -U postgres joat_stores > backup.sql
```
