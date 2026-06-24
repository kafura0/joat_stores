"""
JWT token serializers with store_id + role claims.

StoreTokenObtainPairSerializer:
  - Injects store_id and role into JWT access token payload
  - Platform admins have store_id = None (omitted from claims)
  - store_id is a string UUID, role is one of the 4 Role choices

Implementation: Story 1.5
"""

from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class StoreTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that adds store_id + role claims.

    Access token payload:
      {
        "user_id": "<uuid>",
        "store_id": "<uuid>" | null,
        "role": "platform_admin" | "store_owner" | "store_manager" | "customer",
        ...standard simplejwt claims
      }
    """

    store_id = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="UUID of the store to authenticate against.",
    )

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        if user.store_id:
            token["store_id"] = str(user.store_id)
        else:
            token["store_id"] = None
        if user.platform_user_id:
            token["platform_user_id"] = str(user.platform_user_id)
        else:
            token["platform_user_id"] = None
        return token

    def validate(self, attrs):
        store_id = attrs.pop("store_id", None)

        # Authenticate with email + password
        credentials = {
            self.username_field: attrs.get(self.username_field),
            "password": attrs.get("password"),
        }
        user = authenticate(
            request=self.context.get("request"),
            **credentials,
        )

        if user is None or not user.is_active:
            raise serializers.ValidationError(
                {"message": "Invalid credentials.", "code": "INVALID_CREDENTIALS"}
            )

        # If store_id provided, verify user belongs to that store
        if store_id and user.store_id:
            if str(user.store_id) != str(store_id):
                raise serializers.ValidationError(
                    {
                        "message": "User does not belong to this store.",
                        "code": "STORE_MISMATCH",
                    }
                )

        self.user = user
        refresh = self.get_token(user)

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": str(user.pk),
                "email": user.email,
                "role": user.role,
                "store_id": str(user.store_id) if user.store_id else None,
                "platform_user_id": str(user.platform_user_id) if user.platform_user_id else None,
            },
        }
