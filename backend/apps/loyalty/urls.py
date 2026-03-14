"""Loyalty URL patterns — Epic 10."""

from django.urls import path

from apps.loyalty.views import (
    CustomerProfileDetailView,
    CustomerProfileListView,
    LoyaltyAccountView,
    MyStampCardsView,
    PointsHistoryView,
    RedeemPointsView,
    StampCardListView,
)

app_name = "loyalty"

urlpatterns = [
    # Points
    path("account/", LoyaltyAccountView.as_view(), name="account"),
    path("history/", PointsHistoryView.as_view(), name="history"),
    path("redeem/", RedeemPointsView.as_view(), name="redeem"),
    # Stamp cards
    path("stamp-cards/", StampCardListView.as_view(), name="stamp-cards"),
    path("my-stamp-cards/", MyStampCardsView.as_view(), name="my-stamp-cards"),
    # Customer profiles (store staff)
    path("customers/", CustomerProfileListView.as_view(), name="customer-profiles"),
    path("customers/<str:phone>/", CustomerProfileDetailView.as_view(), name="customer-profile-detail"),
]
