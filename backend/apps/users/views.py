"""
Auth views for JWT token management.

TokenObtainView   — POST /api/v1/auth/token/
                    Returns access token in body, refresh in httpOnly cookie.
TokenRefreshView  — POST /api/v1/auth/token/refresh/
                    Reads refresh from cookie, returns new access + rotates cookie.
LogoutAllView     — POST /api/v1/auth/logout-all/
                    Blacklists all refresh tokens for the user.

Implementation: Story 1.5
"""

from django.conf import settings

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import serializers as drf_serializers

from apps.users.serializers import StoreTokenObtainPairSerializer

# Cookie settings
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = int(
    settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
)
REFRESH_COOKIE_SETTINGS = {
    "key": REFRESH_COOKIE_NAME,
    "httponly": True,
    "secure": not settings.DEBUG,
    "samesite": "Lax",
    "path": "/api/v1/auth/",
    "max_age": REFRESH_COOKIE_MAX_AGE,
}


class TokenObtainView(APIView):
    """
    POST /api/v1/auth/token/

    Authenticates user, returns access token in body,
    sets refresh token as httpOnly cookie.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StoreTokenObtainPairSerializer(
            data=request.data,
            context={"request": request},
        )
        try:
            serializer.is_valid(raise_exception=True)
        except drf_serializers.ValidationError:
            return Response(
                {
                    "errors": [
                        {
                            "field": None,
                            "message": "Invalid credentials.",
                            "code": "INVALID_CREDENTIALS",
                        }
                    ]
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = serializer.validated_data
        refresh_token = data.pop("refresh")

        response = Response(
            {"data": data},
            status=status.HTTP_200_OK,
        )
        response.set_cookie(value=refresh_token, **REFRESH_COOKIE_SETTINGS)
        return response


class TokenRefreshView(APIView):
    """
    POST /api/v1/auth/token/refresh/

    Reads refresh token from httpOnly cookie, returns new access token,
    rotates the refresh cookie. Detects token reuse (family invalidation).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_token:
            return Response(
                {
                    "errors": [
                        {
                            "field": None,
                            "message": "Refresh token not found.",
                            "code": "TOKEN_NOT_FOUND",
                        }
                    ]
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(raw_token)
            # Blacklist the old token (rotation)
            refresh.blacklist()
        except TokenError:
            # Token already blacklisted = reuse detected → invalidate all
            self._invalidate_user_tokens(raw_token)
            response = Response(
                {
                    "errors": [
                        {
                            "field": None,
                            "message": "Token reuse detected. "
                            "All sessions invalidated.",
                            "code": "TOKEN_REUSE_DETECTED",
                        }
                    ]
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
            response.delete_cookie(
                REFRESH_COOKIE_NAME,
                path="/api/v1/auth/",
            )
            return response

        # Issue new tokens with store_id + role claims
        from apps.users.models import User

        try:
            user_obj = User.objects.get(pk=refresh.access_token.payload["user_id"])
            new_refresh = StoreTokenObtainPairSerializer.get_token(user_obj)
        except User.DoesNotExist:
            return Response(
                {
                    "errors": [
                        {
                            "field": None,
                            "message": "User not found.",
                            "code": "USER_NOT_FOUND",
                        }
                    ]
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response(
            {
                "data": {
                    "access": str(new_refresh.access_token),
                }
            },
            status=status.HTTP_200_OK,
        )
        response.set_cookie(value=str(new_refresh), **REFRESH_COOKIE_SETTINGS)
        return response

    def _invalidate_user_tokens(self, raw_token):
        """Invalidate all outstanding tokens for the user (family invalidation)."""
        try:
            from rest_framework_simplejwt.tokens import UntypedToken

            payload = UntypedToken(raw_token).payload
            user_id = payload.get("user_id")
            if user_id:
                tokens = OutstandingToken.objects.filter(user_id=user_id)
                for token in tokens:
                    try:
                        RefreshToken(token.token).blacklist()
                    except TokenError:
                        pass  # already blacklisted
        except (TokenError, InvalidToken):
            pass  # can't decode — nothing to invalidate


class GoogleOAuthCallbackView(APIView):
    """
    Story 4.5 — Google OAuth2 PKCE callback.

    POST /api/v1/auth/google/callback/
    Body: {"code": "<auth_code>", "redirect_uri": "<pkce_redirect>"}

    Flow:
    1. Exchange code for Google access token
    2. Fetch user profile from Google UserInfo
    3. get_or_create store-scoped User with role=CUSTOMER + store from request.store
    4. Return JWT (access in body, refresh in httpOnly cookie)

    Same Google account at two different stores = two separate User records
    (email + store compound uniqueness).
    """

    permission_classes = [AllowAny]

    _GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    _GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    def post(self, request):
        store = getattr(request, "store", None)
        if store is None:
            return Response({"errors": [{"code": "STORE_NOT_FOUND"}]}, status=404)

        code = request.data.get("code", "").strip()
        redirect_uri = request.data.get("redirect_uri", "").strip()
        if not code or not redirect_uri:
            return Response({"errors": [{"code": "CODE_AND_REDIRECT_URI_REQUIRED"}]}, status=400)

        import requests as http_requests

        from django.conf import settings as django_settings

        client_id = getattr(django_settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        client_secret = getattr(django_settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")

        # Exchange authorization code for Google access token
        try:
            token_resp = http_requests.post(self._GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }, timeout=10)
            token_resp.raise_for_status()
            google_access_token = token_resp.json().get("access_token")
        except Exception as exc:
            return Response(
                {"errors": [{"code": "GOOGLE_TOKEN_EXCHANGE_FAILED", "message": str(exc)}]},
                status=502,
            )

        # Fetch user profile
        try:
            userinfo_resp = http_requests.get(
                self._GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
                timeout=10,
            )
            userinfo_resp.raise_for_status()
            profile = userinfo_resp.json()
        except Exception as exc:
            return Response(
                {"errors": [{"code": "GOOGLE_USERINFO_FAILED", "message": str(exc)}]},
                status=502,
            )

        email = profile.get("email", "").lower()
        name = profile.get("name", "")
        if not email:
            return Response({"errors": [{"code": "EMAIL_NOT_PROVIDED_BY_GOOGLE"}]}, status=400)

        # get_or_create store-scoped customer account
        from apps.users.models import User

        user, created = User.objects.get_or_create(
            email=email,
            store=store,
            defaults={
                "first_name": name.split(" ")[0] if name else "",
                "last_name": " ".join(name.split(" ")[1:]) if name else "",
                "role": User.Role.CUSTOMER,
                "is_active": True,
            },
        )

        # Issue JWT
        from apps.users.serializers import StoreTokenObtainPairSerializer

        refresh = StoreTokenObtainPairSerializer.get_token(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response({
            "data": {
                "access": access_token,
                "user_id": str(user.id),
                "email": user.email,
                "name": user.get_full_name() or user.email,
                "created": created,
            }
        })
        response.set_cookie(value=refresh_token, **REFRESH_COOKIE_SETTINGS)
        return response


class LogoutAllView(APIView):
    """
    POST /api/v1/auth/logout-all/

    Blacklists all outstanding refresh tokens for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        tokens = OutstandingToken.objects.filter(user=request.user)
        blacklisted = 0
        for token in tokens:
            try:
                RefreshToken(token.token).blacklist()
                blacklisted += 1
            except TokenError:
                pass  # already blacklisted

        response = Response(
            {"data": {"message": "All sessions invalidated."}},
            status=status.HTTP_200_OK,
        )
        response.delete_cookie(
            REFRESH_COOKIE_NAME,
            path="/api/v1/auth/",
        )
        return response
