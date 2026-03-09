"""
StoreCursorPagination

Cursor-based pagination for all store-scoped list endpoints.
Cursor pagination is stable under concurrent writes (safe for real-time
dashboards and kitchen views).

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

from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class StoreCursorPagination(CursorPagination):
    """
    Cursor-based pagination with {data, meta} envelope.

    All store-scoped list endpoints use this class via TenantViewSet.
    Override ordering per-viewset if needed (default: -created_at).
    """

    page_size = 20
    max_page_size = 100
    ordering = "-created_at"

    def get_paginated_response(self, data):
        # CursorPagination does not guarantee a COUNT query.
        # count is None when unavailable — analytics uses pre-aggregated models.
        try:
            count = self.page.paginator.count
        except Exception:
            count = None

        return Response(
            {
                "data": data,
                "meta": {
                    "count": count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "data": schema,
                "meta": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "nullable": True,
                        },
                        "next": {
                            "type": "string",
                            "nullable": True,
                        },
                        "previous": {
                            "type": "string",
                            "nullable": True,
                        },
                    },
                },
            },
        }
