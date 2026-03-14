"""Payment serializers.

Implementation: Story 2.2
"""

from rest_framework import serializers


class InitiateStkPushSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reference = serializers.CharField(max_length=100)
    method = serializers.ChoiceField(choices=["mpesa"], default="mpesa")
