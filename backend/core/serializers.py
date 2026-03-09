"""
TenantSerializer base class.

Automatically:
  - Strips client-supplied store/store_id from incoming data (cannot be overridden)
  - Injects store from request context on create
  - Never exposes store_id in API responses (internal field)

Usage:
  class ProductSerializer(TenantSerializer):
      class Meta:
          model = Product
          fields = ["id", "name", "price"]  # never include "store" or "store_id"

Implementation: Story 1.3
"""

from rest_framework import serializers


class TenantSerializer(serializers.ModelSerializer):
    """
    Base serializer for all tenant-scoped models.

    The view (TenantViewSet) must pass {"request": request} as serializer
    context so store can be injected on create.
    """

    def to_internal_value(self, data):
        # Strip store/store_id from incoming payload — client cannot set it
        if hasattr(data, "copy"):
            data = data.copy()
        else:
            data = dict(data)
        data.pop("store", None)
        data.pop("store_id", None)
        return super().to_internal_value(data)

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "store") and request.store:
            validated_data["store"] = request.store
        return super().create(validated_data)
