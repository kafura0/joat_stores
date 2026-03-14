"""
Contracting domain serializers.

Stories 6.1-6.6.
"""

from rest_framework import serializers

from apps.contracting.models import (
    AvailabilitySlot,
    Invoice,
    Job,
    JobMilestone,
    Quote,
    QuoteRequest,
    Service,
    ServiceBooking,
)


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "id", "name", "description", "base_price",
            "duration_estimate", "category", "is_active",
        ]
        read_only_fields = ["id"]


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = ["id", "service", "start_time", "end_time", "is_booked"]
        read_only_fields = ["id", "is_booked"]


class ServiceBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceBooking
        fields = [
            "id", "service", "slot", "customer_phone",
            "customer_name", "notes", "status", "created_at",
        ]
        read_only_fields = ["id", "service", "slot", "status", "created_at"]


class QuoteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteRequest
        fields = [
            "id", "customer_phone", "customer_name",
            "description", "service", "status", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = [
            "id", "quote_request", "line_items", "total_amount",
            "valid_until", "notes", "status", "created_at",
        ]
        read_only_fields = ["id", "quote_request", "status", "created_at"]


class JobMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobMilestone
        fields = [
            "id", "title", "description", "status",
            "completion_photo", "notes", "completed_at", "position",
        ]
        read_only_fields = ["id", "status", "completed_at"]


class JobSerializer(serializers.ModelSerializer):
    milestones = JobMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = Job
        fields = [
            "id", "booking", "quote", "assigned_worker",
            "title", "description", "status", "milestones",
            "created_at", "completed_at",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    shareable_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id", "job", "line_items", "total_amount",
            "payment_status", "shareable_url", "created_at", "paid_at",
        ]
        read_only_fields = fields

    def get_shareable_url(self, obj):
        return obj.get_shareable_url()
