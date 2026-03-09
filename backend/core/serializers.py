"""
TenantSerializer base class.

Automatically:
  - Injects store from request context on create
  - Validates that related objects belong to request.store
  - Never exposes store_id in API responses (internal field)

Implementation: Story 1.3
"""
# TODO: Story 1.3 — implement TenantSerializer
