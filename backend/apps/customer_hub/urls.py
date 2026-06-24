"""Customer Hub URL patterns."""

from django.urls import path

from apps.customer_hub.views import (
    FCMRegisterView,
    FCMUnregisterView,
    HubLoginView,
    HubLoyaltyView,
    HubMeView,
    HubOrdersView,
    HubRegisterView,
    HubStoresView,
)

app_name = "customer_hub"

urlpatterns = [
    path("auth/register/", HubRegisterView.as_view(), name="hub-register"),
    path("auth/login/", HubLoginView.as_view(), name="hub-login"),
    path("me/", HubMeView.as_view(), name="hub-me"),
    path("stores/", HubStoresView.as_view(), name="hub-stores"),
    path("orders/", HubOrdersView.as_view(), name="hub-orders"),
    path("loyalty/", HubLoyaltyView.as_view(), name="hub-loyalty"),
    path("fcm/register/", FCMRegisterView.as_view(), name="fcm-register"),
    path("fcm/unregister/", FCMUnregisterView.as_view(), name="fcm-unregister"),
]
