# JOAT Stores — Developer Onboarding Guide

Welcome to JOAT Stores! This guide will get you from zero to productive in under 30 minutes.

---

## Prerequisites

- **Docker Desktop** (or Docker Engine + Compose on Linux)
- **Git**
- **Node.js 18+** (for frontend development outside Docker)
- **Python 3.14+** (for backend development outside Docker)
- A text editor (VS Code recommended)

---

## 1. Clone & Start

```bash
# Clone the repo
git clone https://github.com/kafura0/joat_stores.git
cd joat_stores

# Copy environment template
cp backend/.env.example backend/.env

# Start all services
docker compose up --build
```

This starts 9 services:
| Service | Port | Description |
|---------|------|-------------|
| Django API | :8000 | Backend REST API |
| PostgreSQL | :5432 | Database |
| Redis | :6379 | Cache + Celery broker |
| Celery Worker | — | Async task processing |
| Celery Beat | — | Scheduled tasks |
| Celery Flower | :5555 | Queue monitoring dashboard |
| Storefront | :3000 | Customer-facing Next.js app |
| Admin | :3001 | Merchant dashboard Next.js app |
| Nginx | :80 | Reverse proxy |

---

## 2. Run Migrations & Seed Data

```bash
# In a new terminal
docker compose exec django python manage.py migrate
docker compose exec django python manage.py seed_demo --reset
```

This creates:
- 3 demo stores (retail, restaurant, bar)
- 4 subscription plans
- ~40 products
- 25 backdated orders

---

## 3. Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Platform Admin | `admin@joat.com` | `Demo@1234` |
| Retail Owner | `retail@joat.com` | `Demo@1234` |
| Restaurant Owner | `restaurant@joat.com` | `Demo@1234` |
| Bar Owner | `bar@joat.com` | `Demo@1234` |

---

## 4. Access the Apps

- **Storefront:** http://localhost:3000
- **Admin Dashboard:** http://localhost:3001
- **API Docs (Swagger):** http://localhost/api/v1/docs/
- **Celery Flower:** http://localhost:5555
- **Django Admin:** http://localhost:8000/admin/

---

## 5. Project Structure

```
joat_stores/
├── backend/                    # Django project
│   ├── apps/                   # Domain applications
│   │   ├── store/              # Tenant management
│   │   ├── product/            # Product catalog
│   │   ├── order/              # Orders + cart
│   │   ├── payment/            # M-Pesa integration
│   │   ├── restaurant/         # Restaurant module
│   │   ├── bar/                # Bar tab management
│   │   ├── contracting/        # Service bookings
│   │   ├── saas/               # Plans + subscriptions
│   │   ├── analytics/          # Pre-aggregated analytics
│   │   ├── ai/                 # AI scaffold (501s)
│   │   ├── loyalty/            # Points + stamp cards
│   │   ├── notifications/      # WhatsApp + push
│   │   └── users/              # Auth + RBAC
│   ├── core/                   # TenantModel, TenantMiddleware, base classes
│   └── config/
│       └── settings/
│           ├── base.py         # Shared settings
│           ├── local.py        # Dev overrides
│           └── production.py   # Prod overrides
├── storefront/                 # Next.js customer app
├── admin/                      # Next.js merchant app
├── nginx/                      # Nginx config
├── scripts/                    # Utility scripts
└── _bmad-output/               # BMAD planning + implementation artifacts
```

---

## 6. Key Architecture Concepts

### Multi-Tenancy

Every domain model inherits `TenantModel` which provides:
- UUID primary key
- `store` foreign key (tenant FK)
- Soft delete via `django-safedelete`

**Rule:** Never use `models.Model` directly for tenant-scoped data. Always `TenantModel`.

### Tenant Isolation (5 Layers)

1. **Middleware** — `TenantMiddleware` resolves `request.store` from hostname or `X-Store-ID` header
2. **QuerySet** — `TenantQuerySet` filters by `store_id` automatically
3. **Serializer** — `TenantSerializer` auto-injects `store` from request
4. **Permission** — `IsStoreScoped` enforces store-level access
5. **Admin** — `StoreAdmin` base class restricts data visibility

### RBAC (4 Roles)

| Role | JWT Claim | Access |
|------|-----------|--------|
| Platform Admin | `platform_admin` | All stores, no `store_id` in JWT |
| Store Owner | `store_owner` | Full access to their store |
| Store Manager | `store_manager` | Operational access to their store |
| Customer | `customer` | Store they registered at |

**Rule:** RBAC comes from JWT claims only. Never use `is_staff` or Django groups.

### Celery Queues

| Queue | Purpose |
|-------|---------|
| `order.notifications` | Order confirmations, WhatsApp, loyalty |
| `inventory.alerts` | Low-stock detection |
| `billing.reminders` | Subscription renewal, auto-suspend |
| `payments.reconciliation` | M-Pesa webhook, reconciliation |
| `analytics.reports` | Daily summaries, AI events |

---

## 7. Development Workflow

### Backend Development

```bash
# Run Django shell
docker compose exec django python manage.py shell

# Create superuser
docker compose exec django python manage.py createsuperuser

# Run tests
docker compose exec django pytest

# Run cross-tenant isolation tests
docker compose exec django pytest -k "cross_tenant"

# Lint
docker compose exec django flake8 .
docker compose exec django black --check .
docker compose exec django isort --check .
```

### Frontend Development

```bash
# Install dependencies
cd storefront && npm install
cd admin && npm install

# Run dev server (outside Docker)
cd storefront && npm run dev
cd admin && npm run dev

# Type check
cd storefront && npx tsc --noEmit
cd admin && npx tsc --noEmit
```

### Database Changes

```bash
# Create migration
docker compose exec django python manage.py makemigrations <app_name>

# Apply migration
docker compose exec django python manage.py migrate

# Reset database
docker compose exec django python manage.py seed_demo --reset
```

---

## 8. Common Patterns

### Creating a New Model

```python
# apps/myapp/models.py
from core.models import TenantModel

class MyModel(TenantModel):
    name = models.CharField(max_length=100)
    # store field inherited from TenantModel
```

### Creating a New ViewSet

```python
# apps/myapp/views.py
from core.views import TenantViewSet
from .serializers import MyModelSerializer

class MyModelViewSet(TenantViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
```

### Creating a New Serializer

```python
# apps/myapp/serializers.py
from core.serializers import TenantSerializer
from .models import MyModel

class MyModelSerializer(TenantSerializer):
    class Meta:
        model = MyModel
        fields = ['id', 'name', 'created_at']
```

### Dispatching Celery Tasks

```python
# Always use transaction.on_commit for model-related tasks
from django.db import transaction

transaction.on_commit(lambda: my_task.delay(model.id))
```

### API Response Format

```python
# Single object
return Response({"data": serializer.data})

# List with pagination
return Response({
    "data": serializer.data,
    "meta": {
        "count": queryset.count(),
        "next": next_cursor,
        "previous": previous_cursor
    }
})

# Error
return Response(
    {"errors": [{"field": "phone", "message": "Invalid", "code": "INVALID_PHONE"}]},
    status=status.HTTP_422_UNPROCESSABLE_ENTITY
)
```

---

## 9. Testing

### Backend Tests

```bash
# Run all tests
docker compose exec django pytest

# Run specific app tests
docker compose exec django pytest apps/product/tests/

# Run with coverage
docker compose exec django pytest --cov=apps --cov-report=html

# Run cross-tenant isolation tests (CI gate)
docker compose exec django pytest -k "cross_tenant"
```

### Frontend Tests

No test framework prescribed at MVP. When added:
- Co-locate with component: `ComponentName.test.tsx`
- Wrap in `QueryClientProvider` with fresh `QueryClient`
- Mock `lib/api.ts` axios instance

---

## 10. Environment Variables

### Backend (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgres://...` |
| `REDIS_URL` | Redis connection string | `redis://127.0.0.1:6379/1` |
| `CELERY_BROKER_URL` | Celery broker (same as REDIS_URL) | — |
| `CELERY_RESULT_BACKEND` | Celery result backend | — |
| `DJANGO_SECRET_KEY` | Django secret key | — |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `MPESA_CONSUMER_KEY` | Safaricom Daraja consumer key | — |
| `MPESA_CONSUMER_SECRET` | Safaricom Daraja consumer secret | — |
| `MPESA_SHORTCODE` | M-Pesa shortcode | — |
| `MPESA_PASSKEY` | M-Pesa passkey | — |
| `MPESA_CALLBACK_URL` | Webhook URL | — |

### Frontend (`storefront/.env.local` and `admin/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL |
| `NEXT_PUBLIC_DEMO_MODE` | Enable demo mode (admin only) |

---

## 11. Troubleshooting

### "Connection refused" errors
- Ensure Docker is running
- Check `docker compose ps` for container status
- Verify ports are not in use: `netstat -tlnp | grep -E '80|3000|3001|5432|6379'`

### Database connection errors
- Check PostgreSQL container is healthy
- Verify `DATABASE_URL` in `backend/.env`
- Run `docker compose exec django python manage.py migrate`

### Celery tasks not processing
- Check worker is running: `docker compose logs celery`
- Check Flower at http://localhost:5555
- Verify Redis is accessible

### Frontend can't reach API
- Verify `NEXT_PUBLIC_API_URL` points to `http://localhost/api/v1`
- Check Nginx is proxying correctly
- Check CORS settings in `config/settings/base.py`

---

## 12. Useful Commands

```bash
# Docker
docker compose up -d              # Start in background
docker compose down               # Stop all services
docker compose logs -f django     # Follow Django logs
docker compose ps                 # Check service status

# Django
docker compose exec django python manage.py shell_plus  # Enhanced shell
docker compose exec django python manage.py dbshell     # Database shell
docker compose exec django python manage.py test        # Run tests

# Celery
docker compose exec django celery -A config.celery_app inspect active  # Active tasks
docker compose exec django celery -A config.celery_app inspect stats   # Worker stats

# Redis
docker compose exec redis redis-cli  # Redis CLI
```

---

## 13. Further Reading

- [CLAUDE.md](../CLAUDE.md) — Project context for AI agents
- [API Reference](./api_reference.md) — Complete API documentation
- [Architecture](./architecture.md) — Architecture decision document
- [Data Models](./data_models.md) — Complete data model reference
- [Deployment Guide](./deployment_guide.md) — Production deployment
- [Sales Strategy](./sales_strategy.md) — Go-to-market playbook
- `_bmad-output/` — BMAD planning artifacts (PRD, epics, stories)
