from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PlatformUser, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "role", "store", "platform_user_id", "is_active", "date_joined"]
    list_filter = ["role", "is_active"]
    search_fields = ["email"]
    ordering = ["-date_joined"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Role", {"fields": ("role",)}),
        ("Platform User", {"fields": ("platform_user",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role"),
            },
        ),
    )


@admin.register(PlatformUser)
class PlatformUserAdmin(admin.ModelAdmin):
    list_display = ["email", "phone", "full_name", "created_at"]
    search_fields = ["email", "phone", "full_name"]
    ordering = ["-created_at"]
