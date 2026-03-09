"""
TenantMiddleware

Resolves request.store from:
  1. Hostname (Host header): matches Store.domain
  2. X-Store-ID header: matches Store.id

Sets request.store before any view logic runs.
Returns HTTP 404 if no matching store found.
Returns HTTP 503 if store.status == 'suspended'.

Skips resolution for platform subdomains (admin.joat.com, api.joat.com).

Implementation: Story 1.2
"""
# TODO: Story 1.2 — implement TenantMiddleware
