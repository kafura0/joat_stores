"""
Custom authentication for hub JWT tokens.

Hub tokens carry a `platform_user_id` claim instead of `user_id`.
This auth backend validates the JWT and returns the PlatformUser
as request.user for hub-specific endpoints.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken


class HubJWTAuthentication(BaseAuthentication):
    """
    Authenticates hub JWT tokens carrying `platform_user_id` claim.

    The hub JWT is a standard SimpleJWT AccessToken with:
      {
        "platform_user_id": "<int>",
        "role": "customer",
        "store_id": None,
      }

    After authentication, request.user = PlatformUser instance,
    request.hub_token = validated token payload (dict).
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith(self.keyword):
            return None

        token_str = auth_header.removeprefix(self.keyword).strip()
        if not token_str:
            return None

        try:
            token = AccessToken(token_str)
        except (InvalidToken, TokenError):
            raise AuthenticationFailed({"code": "INVALID_TOKEN", "message": "Token is invalid or expired."})

        platform_user_id = token.get("platform_user_id")
        if not platform_user_id:
            raise AuthenticationFailed({
                "code": "NOT_A_HUB_TOKEN",
                "message": "This token is not a hub token (missing platform_user_id).",
            })

        from apps.users.models import PlatformUser

        try:
            platform_user = PlatformUser.objects.get(pk=platform_user_id, is_active=True)
        except PlatformUser.DoesNotExist:
            raise AuthenticationFailed({"code": "USER_NOT_FOUND", "message": "Platform user not found."})

        request.hub_token = token
        return (platform_user, token)


class HubIsAuthenticated(BaseAuthentication):
    """
    Permission-like mixin: ensures the request has a valid hub JWT.
    Use as: authentication_classes = [HubJWTAuthentication]
    """
    pass
