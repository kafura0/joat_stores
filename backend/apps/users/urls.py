"""
Auth URL configuration.

POST /api/v1/auth/token/          — obtain access + refresh (cookie)
POST /api/v1/auth/token/refresh/  — refresh access token from cookie
POST /api/v1/auth/logout-all/     — invalidate all sessions

Implementation: Story 1.5
"""

from django.urls import path

from apps.users.views import LogoutAllView, TokenObtainView, TokenRefreshView

app_name = "users"

urlpatterns = [
    path("token/", TokenObtainView.as_view(), name="token-obtain"),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path("logout-all/", LogoutAllView.as_view(), name="logout-all"),
]
