"""
Initial contracting app migration.

Creates: Service, AvailabilitySlot, ServiceBooking,
         QuoteRequest, Quote, Job, JobMilestone, Invoice

Stories 6.1-6.6.
"""

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("payment", "0002_add_reversal_reason"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("store", "0005_storesettings_low_stock_threshold"),
    ]

    operations = [
        # ---------------------------------------------------------------- Service
        migrations.CreateModel(
            name="Service",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("base_price", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("duration_estimate", models.PositiveIntegerField()),
                ("category", models.CharField(choices=[("plumbing", "Plumbing"), ("electrical", "Electrical"), ("cleaning", "Cleaning"), ("painting", "Painting"), ("landscaping", "Landscaping"), ("other", "Other")], db_index=True, default="other", max_length=50)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["category", "name"]},
        ),
        migrations.AddIndex(
            model_name="service",
            index=models.Index(fields=["store", "is_active"], name="idx_contracting_service_active"),
        ),

        # -------------------------------------------------------- AvailabilitySlot
        migrations.CreateModel(
            name="AvailabilitySlot",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="slots", to="contracting.service")),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                ("is_booked", models.BooleanField(db_index=True, default=False)),
            ],
            options={"ordering": ["start_time"]},
        ),
        migrations.AddIndex(
            model_name="availabilityslot",
            index=models.Index(fields=["store", "service", "start_time"], name="idx_contracting_slot_service_time"),
        ),

        # -------------------------------------------------------- ServiceBooking
        migrations.CreateModel(
            name="ServiceBooking",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="contracting.service")),
                ("slot", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="booking", to="contracting.availabilityslot")),
                ("customer_phone", models.CharField(max_length=20)),
                ("customer_name", models.CharField(blank=True, default="", max_length=200)),
                ("notes", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("CONFIRMED", "Confirmed"), ("CANCELLED", "Cancelled")], db_index=True, default="PENDING", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="servicebooking",
            index=models.Index(fields=["store", "status"], name="idx_contracting_booking_status"),
        ),

        # ---------------------------------------------------------- QuoteRequest
        migrations.CreateModel(
            name="QuoteRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("customer_phone", models.CharField(max_length=20)),
                ("customer_name", models.CharField(blank=True, default="", max_length=200)),
                ("description", models.TextField()),
                ("service", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quote_requests", to="contracting.service")),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("QUOTED", "Quoted"), ("CLOSED", "Closed")], db_index=True, default="OPEN", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="quoterequest",
            index=models.Index(fields=["store", "status"], name="idx_contracting_quotereq_status"),
        ),

        # --------------------------------------------------------------- Quote
        migrations.CreateModel(
            name="Quote",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("quote_request", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="quote", to="contracting.quoterequest")),
                ("line_items", models.JSONField()),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("valid_until", models.DateField()),
                ("notes", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("QUOTED", "Quoted"), ("ACCEPTED", "Accepted"), ("REJECTED", "Rejected")], db_index=True, default="QUOTED", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="quote",
            index=models.Index(fields=["store", "status"], name="idx_contracting_quote_status"),
        ),

        # ------------------------------------------------------------------ Job
        migrations.CreateModel(
            name="Job",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("booking", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="job", to="contracting.servicebooking")),
                ("quote", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="job", to="contracting.quote")),
                ("assigned_worker", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_jobs", to=settings.AUTH_USER_MODEL)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"), ("SETTLED", "Settled — invoice paid")], db_index=True, default="PENDING", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="job",
            index=models.Index(fields=["store", "status"], name="idx_contracting_job_status"),
        ),

        # ------------------------------------------------------------- JobMilestone
        migrations.CreateModel(
            name="JobMilestone",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="milestones", to="contracting.job")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("COMPLETED", "Completed")], db_index=True, default="PENDING", max_length=20)),
                ("completion_photo", models.ImageField(blank=True, null=True, upload_to="contracting/milestones/")),
                ("notes", models.TextField(blank=True, default="")),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["position", "created_at"]},
        ),

        # --------------------------------------------------------------- Invoice
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("deleted", models.DateTimeField(db_index=True, editable=False, null=True)),
                ("deleted_by_cascade", models.BooleanField(default=False, editable=False)),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(app_label)s_%(class)s_set", to="store.store")),
                ("job", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="invoice", to="contracting.job")),
                ("line_items", models.JSONField()),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("payment_status", models.CharField(choices=[("UNPAID", "Unpaid"), ("PAID", "Paid")], db_index=True, default="UNPAID", max_length=20)),
                ("pdf_file", models.FileField(blank=True, null=True, upload_to="contracting/invoices/")),
                ("shareable_token", models.CharField(blank=True, db_index=True, default="", max_length=200)),
                ("payment_transaction", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="invoices", to="payment.mpesatransaction")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="invoice",
            index=models.Index(fields=["store", "payment_status"], name="idx_contracting_invoice_payment"),
        ),
    ]
