"""
Tests for core.pagination.StoreCursorPagination.
"""

from unittest.mock import MagicMock

from core.pagination import StoreCursorPagination


def make_pagination_with_state(has_next=False, has_previous=False, count=5):
    """Create a StoreCursorPagination instance with pagination state set."""
    pagination = StoreCursorPagination()
    # Set state attributes normally set by paginate_queryset()
    pagination.has_next = has_next
    pagination.has_previous = has_previous
    pagination.cursor = None
    pagination.page = MagicMock()
    pagination.page.paginator.count = count
    pagination.base_url = "http://testserver/"
    pagination.query_params = {}
    return pagination


class TestStoreCursorPagination:
    def test_default_page_size(self):
        """Default page size is 20."""
        assert StoreCursorPagination.page_size == 20

    def test_max_page_size(self):
        """Max page size is 100."""
        assert StoreCursorPagination.max_page_size == 100

    def test_default_ordering(self):
        """Default ordering is -created_at."""
        assert StoreCursorPagination.ordering == "-created_at"

    def test_get_paginated_response_has_data_key(self):
        """Response has 'data' key containing the serialized items."""
        pagination = make_pagination_with_state()
        response = pagination.get_paginated_response(data=[{"id": "abc"}])
        assert "data" in response.data
        assert response.data["data"] == [{"id": "abc"}]

    def test_get_paginated_response_has_meta_key(self):
        """Response has 'meta' key with count, next, previous."""
        pagination = make_pagination_with_state(count=42)
        response = pagination.get_paginated_response(data=[])
        assert "meta" in response.data
        meta = response.data["meta"]
        assert "count" in meta
        assert "next" in meta
        assert "previous" in meta

    def test_get_paginated_response_count_value(self):
        """meta.count matches the paginator's total count."""
        pagination = make_pagination_with_state(count=99)
        response = pagination.get_paginated_response(data=[])
        assert response.data["meta"]["count"] == 99

    def test_get_paginated_response_count_none_on_exception(self):
        """meta.count is None when paginator raises (graceful fallback)."""
        pagination = StoreCursorPagination()
        pagination.has_next = False
        pagination.has_previous = False
        pagination.cursor = None
        pagination.base_url = "http://testserver/"
        pagination.query_params = {}
        # Simulate no page set (count access raises)
        response = pagination.get_paginated_response(data=[])
        assert response.data["meta"]["count"] is None

    def test_paginated_response_schema_shape(self):
        """get_paginated_response_schema returns correct envelope shape."""
        pagination = StoreCursorPagination()
        schema = {"type": "array", "items": {"type": "object"}}
        result = pagination.get_paginated_response_schema(schema)
        assert result["type"] == "object"
        assert "data" in result["properties"]
        assert "meta" in result["properties"]
        meta_props = result["properties"]["meta"]["properties"]
        assert "count" in meta_props
        assert "next" in meta_props
        assert "previous" in meta_props
