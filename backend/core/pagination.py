"""
StoreCursorPagination

Cursor-based pagination for all store-scoped list endpoints.
Cursor pagination is stable under concurrent writes (safe for real-time dashboards).

Response envelope:
  {
    "data": [...],
    "meta": {
      "count": 150,
      "next": "cursor_token_or_null",
      "previous": "cursor_token_or_null"
    }
  }

Default page size: 20. Max: 100.

Implementation: Story 1.3
"""
# TODO: Story 1.3 — implement StoreCursorPagination
