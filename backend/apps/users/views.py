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
