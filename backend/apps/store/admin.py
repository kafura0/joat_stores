from django.contrib import admin

from apps.store.models import Store, StoreSettings, StoreTheme


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "domain",
        "tenant_type",
        "status",
        "country",
        "currency",
    ]
    list_filter = ["tenant_type", "status", "country"]
    search_fields = ["name", "slug", "domain"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["name"]


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ["store"]
    raw_id_fields = ["store"]


@admin.register(StoreTheme)
class StoreThemeAdmin(admin.ModelAdmin):
    list_display = ["store"]
    raw_id_fields = ["store"]
