"""
Customer Hub views — cross-tenant customer portal.

POST /api/v1/hub/auth/register/   — create PlatformUser account
POST /api/v1/hub/auth/login/      — login, returns hub JWT
GET  /api/v1/hub/me/              — PlatformUser profile
GET  /api/v1/hub/stores/          — stores the customer has engaged with
GET  /api/v1/hub/orders/          — cross-store order history
GET  /api/v1/hub/loyalty/         — cross-store loyalty summary
"""

import structlog
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.customer_hub.auth import HubJWTAuthentication
from apps.customer_hub.serializers import (
    HubLoyaltySerializer,
    HubOrderSerializer,
    HubRegisterSerializer,
    LinkedStoreSerializer,
    PlatformUserSerializer,
)
from apps.loyalty.models import LoyaltyAccount
from apps.notifications.models import FCMDevice
from apps.order.models import Order
from apps.users.models import PlatformUser, User

logger = structlog.get_logger(__name__)


def _issue_hub_token(platform_user: PlatformUser) -> dict:
    """
    Issue a hub JWT carrying platform_user_id.
    Uses RefreshToken directly (not tied to a Django User).
    """
    refresh = RefreshToken()
    refresh["platform_user_id"] = str(platform_user.pk)
    refresh["role"] = "customer"
    refresh["store_id"] = None
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class HubRegisterView(APIView):
    """POST /api/v1/hub/auth/register/"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = HubRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower().strip()
        password = serializer.validated_data["password"]
        full_name = serializer.validated_data.get("full_name", "")
        phone = serializer.validated_data.get("phone", "")

        if PlatformUser.objects.filter(email=email).exists():
            return Response(
                {"errors": [{"code": "EMAIL_EXISTS", "message": "A user with this email already exists."}]},
                status=status.HTTP_409_CONFLICT,
            )

        platform_user = PlatformUser(email=email, full_name=full_name, phone=phone or None)
        platform_user.set_password(password)
        platform_user.save()

        tokens = _issue_hub_token(platform_user)

        return Response(
            {
                "data": {
                    "access": tokens["access"],
                    "user": {
                        "id": platform_user.pk,
                        "email": platform_user.email,
                        "full_name": platform_user.full_name,
                    },
                }
            },
            status=status.HTTP_201_CREATED,
        )


class HubLoginView(APIView):
    """POST /api/v1/hub/auth/login/"""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").lower().strip()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"errors": [{"code": "EMAIL_AND_PASSWORD_REQUIRED"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            platform_user = PlatformUser.objects.get(email=email, is_active=True)
        except PlatformUser.DoesNotExist:
            return Response(
                {"errors": [{"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}]},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not platform_user.check_password(password):
            return Response(
                {"errors": [{"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}]},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = _issue_hub_token(platform_user)

        return Response(
            {
                "data": {
                    "access": tokens["access"],
                    "refresh": tokens["refresh"],
                    "user": {
                        "id": platform_user.pk,
                        "email": platform_user.email,
                        "full_name": platform_user.full_name,
                    },
                }
            }
        )


class HubMeView(APIView):
    """GET /api/v1/hub/me/"""

    authentication_classes = [HubJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        platform_user = request.user
        return Response({
            "data": PlatformUserSerializer(platform_user).data,
        })


class HubStoresView(APIView):
    """GET /api/v1/hub/stores/ — stores this customer has engaged with."""

    authentication_classes = [HubJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        platform_user = request.user

        store_users = User.objects.filter(
            platform_user=platform_user,
            store__isnull=False,
            role="customer",
        ).select_related("store").order_by("store__name")

        stores = [su.store for su in store_users if su.store is not None]

        return Response({
            "data": LinkedStoreSerializer(stores, many=True).data,
        })


class HubOrdersView(APIView):
    """GET /api/v1/hub/orders/ — cross-store order history."""

    authentication_classes = [HubJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        platform_user = request.user

        store_user_ids = User.objects.filter(
            platform_user=platform_user,
        ).values_list("pk", flat=True)

        orders = Order.objects.filter(
            customer_id__in=list(store_user_ids),
        ).select_related("store").order_by("-created_at")[:100]

        return Response({
            "data": HubOrderSerializer(orders, many=True).data,
        })


class HubLoyaltyView(APIView):
    """GET /api/v1/hub/loyalty/ — cross-store loyalty summary."""

    authentication_classes = [HubJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        platform_user = request.user

        store_user_phones = User.objects.filter(
            platform_user=platform_user,
        ).exclude(
            customer_profiles__customer_phone=""
        ).values_list(
            "customer_profiles__customer_phone", flat=True
        ).distinct()

        phones = set()
        phones.update(p for p in store_user_phones if p)
        if platform_user.phone:
            phones.add(platform_user.phone)

        if not phones:
            return Response({"data": []})

        accounts = LoyaltyAccount.objects.filter(
            customer_phone__in=list(phones),
        ).select_related("store").order_by("-lifetime_earned")

        return Response({
            "data": HubLoyaltySerializer(accounts, many=True).data,
        })


class FCMRegisterView(APIView):
    """POST /api/v1/hub/fcm/register/ — register device for push notifications."""

    authentication_classes = [HubJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        platform_user = request.user
        registration_id = request.data.get("registration_id", "").strip()
        platform = request.data.get("platform", FCMDevice.PLATFORM_ANDROID)

        if not registration_id:
            return Response(
                {"errors": [{"code": "REGISTRATION_ID_REQUIRED"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device, created = FCMDevice.objects.get_or_create(
            platform_user=platform_user,
            registration_id=registration_id,
            defaults={"platform": platform, "is_active": True},
        )
        if not created:
            device.is_active = True
            device.platform = platform
            device.save(update_fields=["is_active", "platform"])

        return Response({
            "data": {
                "id": device.pk,
                "platform": device.platform,
                "created": created,
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class FCMUnregisterView(APIView):
    """POST /api/v1/hub/fcm/unregister/ — deactivate device."""

    authentication_classes = [HubJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        platform_user = request.user
        registration_id = request.data.get("registration_id", "").strip()

        if not registration_id:
            return Response(
                {"errors": [{"code": "REGISTRATION_ID_REQUIRED"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated = FCMDevice.objects.filter(
            platform_user=platform_user,
            registration_id=registration_id,
        ).update(is_active=False)

        return Response({
            "data": {"deactivated": updated > 0},
        })
