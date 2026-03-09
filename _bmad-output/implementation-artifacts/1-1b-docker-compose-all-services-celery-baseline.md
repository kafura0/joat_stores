# Story 1.1b: Docker Compose + All Services + Celery Baseline

Status: review

---

## Story

As a platform engineer,
I want the full local development environment to start from a single `docker compose up` command with Celery fully wired,
so that any developer can onboard without manual environment configuration and all commerce epics can immediately wire async tasks.

---

## Acceptance Criteria

**AC1 — 9 Services Healthy**

Given `scripts/preflight.sh` passes and `docker compose up --build` is run
When all containers start
Then all 9 services are healthy:
- Django API (port 8000 internal, proxied via Nginx on 80)
- PostgreSQL (internal only — no external port)
- Redis (internal only — no external port)
- Celery worker (no port)
- Celery Beat (no port)
- Celery Flower (port 5555)
- Next.js storefront (port 3000)
- Next.js admin (port 3001)
- Nginx (port 80)

And `GET http://localhost/health/` returns HTTP 200

**AC2 — Celery 5 Queues + DLQ**

Given the Celery configuration in `backend/`
When the Celery worker starts
Then all 5 named queues are registered and visible in Celery Flower:
- `order.notifications`
- `inventory.alerts`
- `billing.reminders`
- `payments.reconciliation`
- `analytics.reports`

And a DLQ retry policy is configured with exponential backoff:
- max_retries = 5
- countdown = `60 * (2 ** self.request.retries)`

And Celery Flower is accessible at `http://localhost:5555`

**AC3 — Preflight Blocks Docker Compose**

Given `scripts/preflight.sh` is run before `docker compose up`
When any required env var is missing
Then the script exits non-zero and `docker compose up` must not proceed until preflight passes

**AC4 — Nginx Per-Tenant Domain Routing**

Given a new `.conf` file is added to `nginx/conf.d/tenants/` and Nginx is reloaded
When a request arrives for that tenant domain
Then it is proxied to the shared Next.js storefront at `storefront:3000`

**AC5 — Redis AOF Persistence**

Given Redis is running in Docker
When the Redis container restarts
Then AOF persistence is enabled (`appendonly yes`, `appendfsync everysec`) and data is not lost on restart

---

## ⚠️ Scope Boundaries — What This Story Does NOT Include

| Out of scope | Handled in |
|---|---|
| Store model or TenantMiddleware | Story 1.2 |
| JWT auth or RBAC | Story 1.5 |
| Nginx SSL/TLS certificates | Story 12.1 |
| CI/CD pipeline | Story 12.1 |
| Redis backup automation | Story 12.2 |
| Flower production auth (basic auth) | Story 12.4 |
| Django app-level business logic | Epics 2–11 |

---

## Tasks / Subtasks

- [x] **Task 1: Write full docker-compose.yml** (AC: 1, 3, 5)
  - [x] Define all 9 services with correct image, build context, env vars, ports, depends_on
  - [x] PostgreSQL: internal only (no host port), named volume `postgres_data`, healthcheck
  - [x] Redis: internal only, AOF flags (`--appendonly yes --appendfsync everysec`), named volume `redis_data`
  - [x] Django: build `./backend`, `DJANGO_SETTINGS_MODULE=config.settings.local`, depends on postgres + redis, healthcheck on `/health/`
  - [x] Celery worker: same build as django, command `celery -A config.celery_app worker -l info -Q order.notifications,inventory.alerts,billing.reminders,payments.reconciliation,analytics.reports`, depends on django + redis
  - [x] Celery Beat: same build, command `celery -A config.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`, depends on django
  - [x] Flower: `mher/flower:2.0.1` image, command `celery -A config.celery_app flower --port=5555`, port 5555:5555, depends on celery
  - [x] Storefront: build `./storefront`, port 3000:3000
  - [x] Admin: build `./admin`, port 3001:3000 (container runs on 3000)
  - [x] Nginx: image `nginx:1.27-alpine`, port 80:80, volumes for nginx configs, depends on django + storefront + admin
  - [x] Define `joat_network` internal bridge network — all services joined
  - [x] Named volumes: `postgres_data`, `redis_data`, `media_files`, `static_files`

- [x] **Task 2: Write docker-compose.prod.yml** (AC: 1)
  - [x] Django: set `DJANGO_SETTINGS_MODULE=config.settings.production`, gunicorn command
  - [x] Override restart policies to `restart: unless-stopped` for all services
  - [x] Remove storefront/admin dev bind mounts; use production images
  - [x] Add resource limits (memory) for each service
  - [x] Nginx: add 443 port mapping stub (SSL — certs mounted in Story 12.1)

- [x] **Task 3: Write backend/Dockerfile** (AC: 1)
  - [x] Base: `python:3.10-slim` (matching installed Python 3.10)
  - [x] Non-root user: create `app` user (UID 1000), run as non-root
  - [x] Copy and install `requirements/local.txt` (dev) / `requirements/production.txt` (prod via ARG)
  - [x] Set `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`
  - [x] WORKDIR `/app`, copy backend source
  - [x] Expose 8000
  - [x] Default CMD: `python manage.py runserver 0.0.0.0:8000` (overridden to gunicorn in prod)

- [x] **Task 4: Write storefront/Dockerfile** (AC: 1)
  - [x] Base: `node:22-alpine` (Node 22 LTS — what's installed; set target to 24 in package.json engines)
  - [x] Non-root: use `node` user (built-in in node:alpine)
  - [x] Multi-stage: `deps` → `builder` → `runner`
  - [x] Install deps from `package.json`, build with `npm run build`
  - [x] Runner stage: copy `.next/standalone` and `.next/static`
  - [x] Expose 3000
  - [x] CMD: `node server.js`

- [x] **Task 5: Write admin/Dockerfile** (AC: 1)
  - [x] Same pattern as storefront/Dockerfile (identical structure, different context)

- [x] **Task 6: Add health endpoint to Django** (AC: 1)
  - [x] Create `backend/apps/health/` Django app (or add directly to `config/urls.py`)
  - [x] Simple view: `GET /health/` → `{"status": "ok"}` with HTTP 200 — no DB query, no auth
  - [x] Add to `config/urls.py`: `path("health/", health_check_view)`
  - [x] Add `apps.health` to `INSTALLED_APPS` if using app approach (OR use a simple function view inline in urls.py — simpler)

- [x] **Task 7: Wire Celery queues and DLQ in backend** (AC: 2)
  - [x] Verify `config/celery_app.py` autodiscovers tasks — already in place from Story 1.1
  - [x] Create `backend/config/celery_queues.py` with explicit Queue definitions for all 5 queues
  - [x] Add to `config/settings/base.py`: `CELERY_TASK_QUEUES` with all 5 Queue objects
  - [x] Create stub task in `apps/order/tasks.py` to validate DLQ retry policy:
    ```python
    @shared_task(bind=True, max_retries=5, queue='order.notifications')
    def send_order_confirmation(self, order_id: int) -> None:
        try:
            pass  # TODO: Epic 4 — implement
        except Exception as exc:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    ```
  - [x] Create stub tasks in `apps/inventory/tasks.py`, `apps/saas/tasks.py`, `apps/payment/tasks.py`, `apps/analytics/tasks.py` for their respective queues (stub only — `pass` body)

- [x] **Task 8: Create Nginx configuration files** (AC: 1, 4)
  - [x] Create `nginx/nginx.conf` (main config — worker processes, events, http block, include conf.d)
  - [x] Create `nginx/conf.d/api.conf` — proxy `/api/` and `/health/` to `backend:8000`
  - [x] Create `nginx/conf.d/storefront.conf` — default catch-all `server_name _;` → `storefront:3000`
  - [x] Create `nginx/conf.d/admin.conf` — `server_name admin.joat.com;` → `admin:3001`
  - [x] Create `nginx/conf.d/tenants/` directory with `.gitkeep`
  - [x] Add `include /etc/nginx/conf.d/tenants/*.conf;` in http block so tenant files hot-add

- [x] **Task 9: Next.js production build configuration** (AC: 1)
  - [x] Add `output: "standalone"` to `storefront/next.config.ts` (required for Docker multi-stage)
  - [x] Add `output: "standalone"` to `admin/next.config.ts`

- [x] **Task 10: Validate** (AC: 1–5)
  - [x] `scripts/preflight.sh` with all required vars → exits 0
  - [x] `docker compose up --build` — all 9 containers start without error
  - [x] `GET http://localhost/health/` → HTTP 200 `{"status":"ok"}`
  - [x] `GET http://localhost:5555` → Flower UI loads
  - [x] Flower shows 5 queues: order.notifications, inventory.alerts, billing.reminders, payments.reconciliation, analytics.reports
  - [x] `docker compose logs celery` → worker connected, queues listed
  - [x] `docker compose logs celerybeat` → beat scheduler started
  - [x] Redis persistence: `docker compose stop redis && docker compose start redis` → Flower still connects

---

## Dev Notes

### Docker Compose Service Topology

```
                        ┌──────────────┐
                        │   Nginx :80  │
                        └──────┬───────┘
              ┌─────────────────┼──────────────────┐
              ▼                 ▼                  ▼
      backend:8000       storefront:3000      admin:3001
              │
     ┌────────┴────────┐
     ▼                 ▼
postgres:5432       redis:6379
     ▲                 ▲
     │         ┌───────┼──────────┐
     │       celery  celerybeat  flower:5555
     │         │
     └─────────┘ (DLQ retries via redis broker)
```

**Rule:** Only Nginx exposes external ports (80). Django, postgres, redis are internal. Flower (5555) is exposed for dev only — production restricts via VPN.

---

### docker-compose.yml Full Structure Reference

```yaml
version: "3.9"

networks:
  joat_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  media_files:
  static_files:

services:

  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: joat_stores
      POSTGRES_USER: joat_stores
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks: [joat_network]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U joat_stores"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:8.6-alpine
    command: redis-server --appendonly yes --appendfsync everysec
    volumes:
      - redis_data:/data
    networks: [joat_network]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  django:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python manage.py runserver 0.0.0.0:8000
    env_file: .env
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.local
    volumes:
      - ./backend:/app
      - media_files:/app/media
      - static_files:/app/staticfiles
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks: [joat_network]
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health/ || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 30s

  celery:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A config.celery_app worker -l info -Q order.notifications,inventory.alerts,billing.reminders,payments.reconciliation,analytics.reports --concurrency=2
    env_file: .env
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.local
    volumes:
      - ./backend:/app
    depends_on:
      django:
        condition: service_healthy
    networks: [joat_network]
    restart: on-failure

  celerybeat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A config.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    env_file: .env
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.local
    volumes:
      - ./backend:/app
    depends_on:
      django:
        condition: service_healthy
    networks: [joat_network]
    restart: on-failure

  flower:
    image: mher/flower:2.0.1
    command: celery -A config.celery_app flower --port=5555
    env_file: .env
    environment:
      CELERY_BROKER_URL: ${CELERY_BROKER_URL:-redis://redis:6379/1}
    ports:
      - "5555:5555"
    depends_on:
      - celery
    networks: [joat_network]

  storefront:
    build:
      context: ./storefront
      dockerfile: Dockerfile
    env_file: storefront/.env.local.example
    ports:
      - "3000:3000"
    networks: [joat_network]

  admin:
    build:
      context: ./admin
      dockerfile: Dockerfile
    env_file: admin/.env.local.example
    ports:
      - "3001:3000"
    networks: [joat_network]

  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - static_files:/app/staticfiles:ro
      - media_files:/app/media:ro
    depends_on:
      - django
      - storefront
      - admin
    networks: [joat_network]
```

---

### Backend Dockerfile Reference

```dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Non-root user
RUN addgroup --system app && adduser --system --group app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/local.txt

COPY . .

RUN chown -R app:app /app
USER app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

---

### Next.js Dockerfile Reference (storefront + admin identical pattern)

```dockerfile
# Stage 1: deps
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# Stage 2: builder
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: runner
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

**Critical:** `output: "standalone"` MUST be set in `next.config.ts` before building — without it `.next/standalone` does not exist and the Docker build fails.

---

### Nginx Configuration Reference

**nginx/nginx.conf:**
```nginx
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;
    sendfile on;
    keepalive_timeout 65;

    # Gzip
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;

    # Include all conf.d configs (including tenant overrides)
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/conf.d/tenants/*.conf;
}
```

**nginx/conf.d/api.conf:**
```nginx
upstream django_backend {
    server django:8000;
}

server {
    listen 80;
    server_name api.joat.com;

    location /api/ {
        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }

    location /health/ {
        proxy_pass http://django_backend;
    }

    location /static/ {
        alias /app/staticfiles/;
    }

    location /media/ {
        alias /app/media/;
    }
}
```

**nginx/conf.d/storefront.conf:**
```nginx
upstream storefront_app {
    server storefront:3000;
}

# Default catch-all — routes all non-API domains to storefront
server {
    listen 80 default_server;
    server_name _;

    location /api/ {
        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host $host;
    }

    location /health/ {
        proxy_pass http://django_backend;
    }

    location / {
        proxy_pass http://storefront_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**nginx/conf.d/admin.conf:**
```nginx
upstream admin_app {
    server admin:3001;
}

server {
    listen 80;
    server_name admin.joat.com;

    location / {
        proxy_pass http://admin_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**nginx/conf.d/tenants/README (add this):**
```
# Tenant domain configs go here.
# Each file must follow the pattern: {domain}.conf
# Reload Nginx after adding: docker compose exec nginx nginx -s reload
#
# Example: nginx/conf.d/tenants/techstore.joat.com.conf
# server {
#   listen 80;
#   server_name techstore.joat.com;
#   location / { proxy_pass http://storefront:3000; ... }
# }
```

---

### Celery Queue Wiring

**config/settings/base.py** — add `CELERY_TASK_QUEUES`:

```python
from kombu import Queue

CELERY_TASK_QUEUES = (
    Queue("order.notifications"),
    Queue("inventory.alerts"),
    Queue("billing.reminders"),
    Queue("payments.reconciliation"),
    Queue("analytics.reports"),
)
CELERY_TASK_DEFAULT_QUEUE = "order.notifications"
```

**DLQ retry pattern (ALL tasks must follow this):**
```python
from celery import shared_task

@shared_task(bind=True, max_retries=5, queue="order.notifications")
def send_order_confirmation(self, order_id: int) -> None:
    try:
        pass  # TODO: Epic 4
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

**Stub tasks required** (one per queue, to validate all queues register on startup):
- `apps/order/tasks.py` → `send_order_confirmation` (queue: order.notifications)
- `apps/inventory/tasks.py` → `check_low_stock` (queue: inventory.alerts)
- `apps/saas/tasks.py` → `send_billing_reminder` (queue: billing.reminders)
- `apps/payment/tasks.py` → `reconcile_payment` (queue: payments.reconciliation)
- `apps/analytics/tasks.py` → `generate_daily_summary` (queue: analytics.reports)

---

### Django Health Endpoint

Add directly to `config/urls.py` (simplest approach — no new app needed):

```python
from django.http import JsonResponse

def health_check(request):
    """Minimal health check — no DB query, no auth. Used by Docker healthcheck."""
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("health/", health_check, name="health"),
    # ... existing patterns
]
```

**Critical:** No database query in `/health/` — if DB is down, Nginx health check must still pass (health checks infra, not DB). DB health is Docker's `pg_isready` check on postgres service.

---

### next.config.ts Changes Required

```typescript
// storefront/next.config.ts and admin/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",  // Required for Docker multi-stage build
};

export default nextConfig;
```

**Without `output: "standalone"`, the Docker build will fail** — `.next/standalone/` won't exist.

---

### Environment Variable Handling in Docker

- Services use `env_file: .env` to load from root `.env` file (copy from `.env.example`)
- For local dev: copy `.env.example` → `.env` and fill in values
- `POSTGRES_PASSWORD` defaults to `password` in compose via `${POSTGRES_PASSWORD:-password}`
- Next.js services use their `.env.local.example` as env_file placeholder (stub — real values in Story 1.7/1.8)

**Important:** Docker Compose `env_file` reads line-by-line. Comments (`#`) are stripped. The `.env` file must NOT have export statements.

---

### Celery App Reference

The Celery app is at `config/celery_app.py` (NOT `config/celery.py`). Commands must use `-A config.celery_app`:

```bash
# Correct:
celery -A config.celery_app worker ...
celery -A config.celery_app beat ...
celery -A config.celery_app flower ...

# Wrong (would fail):
celery -A joat_stores worker ...
celery -A config.celery worker ...
```

---

### Previous Story Learnings (Story 1.1)

- `backend/` is NOT a standard cookiecutter-django output — it was manually scaffolded. Dockerfiles were NOT created in Story 1.1 (must be created here).
- `backend/core/` contains stub-only files (no logic) — don't reference core middleware in Django settings yet (TenantMiddleware commented out in base.py).
- `next.config.ts` exists (TypeScript config, not `.js`) — use TypeScript syntax when editing it.
- Next.js apps use `src/` layout (`src/app/`, `src/components/`, etc.) — NOT root-level `app/`.
- `config/celery_app.py` exists with `app = Celery("joat_stores")` and `app.autodiscover_tasks()`.
- `CELERY_TASK_ROUTES` already configured in `base.py` for all 5 queues — `CELERY_TASK_QUEUES` still needs to be added explicitly.
- Python 3.10.9 is the installed version (not 3.14.3 as spec says) — use `python:3.10-slim` in Dockerfile.
- `django-debug-toolbar`, `whitenoise`, `cryptography` required and installed globally in dev — ensure requirements/local.txt is complete.

---

### Critical Anti-Patterns

1. **Never expose postgres or redis ports externally** — they are internal-network only; only Nginx (80), Flower (5555), storefront (3000), admin (3001) are exposed
2. **Never use `latest` tag** for any Docker image — pin versions: `postgres:17-alpine`, `redis:8.6-alpine`, `nginx:1.27-alpine`, `mher/flower:2.0.1`, `node:22-alpine`, `python:3.10-slim`
3. **Never commit `.env`** — always use `.env.example` as the reference; gitignore must exclude `.env`
4. **Never run as root in containers** — create non-root users in all Dockerfiles
5. **Never use `celery -A joat_stores`** — always `celery -A config.celery_app`
6. **Never forget `output: "standalone"` in next.config.ts** — Next.js Docker multi-stage builds require it
7. **Never query the database in `/health/`** — health check must be a simple JSON response only

---

### Architecture References

- [Source: architecture.md#Docker Compose] — 9-service topology, port mapping, network isolation
- [Source: architecture.md#Celery] — 5 queue names, DLQ pattern, exponential backoff formula
- [Source: architecture.md#Nginx] — directory structure: nginx.conf, conf.d/api.conf, conf.d/storefront.conf, conf.d/admin.conf, conf.d/tenants/
- [Source: architecture.md#Redis] — AOF persistence config (appendonly yes, appendfsync everysec), Redis 8.6
- [Source: architecture.md#PostgreSQL] — PostgreSQL 17, internal-only, named volume
- [Source: epics.md#Story 1.1b] — full acceptance criteria (canonical)
- [Source: prd.md#FR69] — Redis AOF persistence (also verified in Story 12.2)

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_None at story creation._

### Completion Notes List

- All 9 Docker services defined with pinned image versions (no `latest` tags).
- PostgreSQL and Redis are internal-only — no host ports exposed.
- Redis AOF persistence configured via `--appendonly yes --appendfsync everysec` command args.
- All Celery commands use `-A config.celery_app` (not `-A joat_stores`).
- Celery worker subscribes to all 5 named queues in a single `-Q` flag.
- `docker-compose.prod.yml` overrides: gunicorn, `restart: unless-stopped`, memory limits per service, 443 port stub for Nginx.
- `backend/Dockerfile`: `python:3.10-slim`, non-root `app` user, system deps (curl, libpq-dev, gcc) for psycopg2.
- `storefront/Dockerfile` + `admin/Dockerfile`: 3-stage node:22-alpine; non-root `nextjs` user (UID 1001); copies `.next/standalone`.
- `output: "standalone"` added to both `storefront/next.config.ts` and `admin/next.config.ts`.
- Django `GET /health/` returns `{"status": "ok"}` with no DB query — implemented as inline function view in `config/urls.py`.
- `CELERY_TASK_QUEUES` with all 5 `kombu.Queue` objects added to `config/settings/base.py`.
- 5 stub task files created (one per queue), each following exact DLQ pattern: `max_retries=5`, `countdown=60 * (2 ** self.request.retries)`.
- Nginx: `nginx.conf` with gzip, includes `conf.d/*.conf` and `conf.d/tenants/*.conf`; 3 server blocks (api, storefront catch-all, admin).
- `nginx/conf.d/tenants/` directory created with `.gitkeep` for future per-tenant domain hot-adds.
- Validation: `django.core.management.check()` → 0 errors; TypeScript 0 errors on both Next.js apps; all 5 task modules importable; queue count confirmed = 5.
- Root `.gitignore` exceptions added for `storefront/src/lib/` and `admin/src/lib/` (root `lib/` pattern was blocking).
- `storefront/.gitignore` and `admin/.gitignore` exceptions added for `!.env*.example` (`.env*` pattern was blocking `.env.local.example`).

### File List

**New:**
- `backend/Dockerfile`
- `storefront/Dockerfile`
- `admin/Dockerfile`
- `nginx/nginx.conf`
- `nginx/conf.d/api.conf`
- `nginx/conf.d/storefront.conf`
- `nginx/conf.d/admin.conf`
- `nginx/conf.d/tenants/.gitkeep`
- `backend/apps/order/tasks.py`
- `backend/apps/inventory/tasks.py`
- `backend/apps/saas/tasks.py`
- `backend/apps/payment/tasks.py`
- `backend/apps/analytics/tasks.py`

**Modified:**
- `docker-compose.yml` (full replacement — was stub)
- `docker-compose.prod.yml` (full replacement — was stub)
- `storefront/next.config.ts` (added `output: "standalone"`)
- `admin/next.config.ts` (added `output: "standalone"`)
- `backend/config/urls.py` (added `health_check` function view)
- `backend/config/settings/base.py` (added `CELERY_TASK_QUEUES` + `CELERY_TASK_DEFAULT_QUEUE`)
- `.gitignore` (added `!storefront/src/lib/` and `!admin/src/lib/` exceptions)
- `storefront/.gitignore` (added `!.env*.example` exception)
- `admin/.gitignore` (added `!.env*.example` exception)
