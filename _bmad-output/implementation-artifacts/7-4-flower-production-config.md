# Story 7.4 — Celery Flower Production Config

## Overview

Celery Flower is secured with HTTP Basic Auth and configured for persistent task
history. Credentials come from environment variables — never hardcoded.

## Docker Compose Addition

Add to `docker-compose.yml` under `services:`:

```yaml
flower:
  image: mher/flower:2.0
  command: >
    celery
    --broker=${CELERY_BROKER_URL}
    flower
    --basic_auth=${FLOWER_USER}:${FLOWER_PASSWORD}
    --persistent=true
    --db=/flower-data/flower.db
    --url_prefix=flower
  environment:
    - CELERY_BROKER_URL=${CELERY_BROKER_URL}
    - FLOWER_USER=${FLOWER_USER}
    - FLOWER_PASSWORD=${FLOWER_PASSWORD}
  volumes:
    - flower_data:/flower-data
  ports:
    - "5555:5555"
  depends_on:
    - redis
  restart: unless-stopped
```

Add to `volumes:` at the bottom:
```yaml
volumes:
  flower_data:
```

## Nginx Proxy (Optional — restrict to internal network)

```nginx
location /flower/ {
    proxy_pass http://flower:5555/flower/;
    proxy_set_header Host $host;
    proxy_redirect off;
    # Restrict to VPN/internal IPs
    allow 10.0.0.0/8;
    deny all;
}
```

## Environment Variables (add to .env.example)

```
FLOWER_USER=admin
FLOWER_PASSWORD=<strong-random-password>
```

## DLQ Visibility

Failed tasks in the DLQ (Redis sorted set `celery:dlq`) are visible in Flower's
task list. Operators can inspect the exception traceback and manually retry or
discard failed tasks.

## Task History Persistence

`--persistent=true --db=/flower-data/flower.db` stores task history in SQLite
on the named volume. History survives container restarts.

## Implementation Status

- [x] DLQ routing in `core/tasks.py::DLQTask.on_failure`
- [x] Exponential backoff in `core/tasks.py::DLQTask.retry`
- [x] Sentry capture on max-retries exceeded
- [x] Flower docker service (this artifact)
- [ ] Add FLOWER_USER + FLOWER_PASSWORD to docker-compose.yml (deploy time)
