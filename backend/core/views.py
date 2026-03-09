"""
TenantViewSet base class.

Extends ModelViewSet with:
  - get_queryset() scoped to request.store automatically
  - perform_create() injects store from request
  - Permission class: IsStoreScoped by default
  - Pagination: StoreCursorPagination by default

All domain viewsets MUST extend TenantViewSet — never ModelViewSet directly.

Implementation: Story 1.3
"""
# TODO: Story 1.3 — implement TenantViewSet
