"""
User management views for store owners/managers.

GET    /api/v1/users/       — list staff for current store
POST   /api/v1/users/       — create staff member (free for now)
GET    /api/v1/users/{id}/  — get staff detail
PATCH  /api/v1/users/{id}/  — update staff
DELETE /api/v1/users/{id}/  — deactivate staff

Implementation: Story 1.8 + Admin user management
"""

from django.contrib.auth.hashers import make_password
from django.db.models import Q

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User


class IsStoreOwnerOrManager(permissions.BasePermission):
    """Only store_owner or store_manager can manage staff."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            User.Role.STORE_OWNER,
            User.Role.STORE_MANAGER,
            User.Role.PLATFORM_ADMIN,
        )


class UserManagementView(APIView):
    """
    GET  /api/v1/users/  — list staff for the current store
    POST /api/v1/users/  — create staff member
    """

    permission_classes = [permissions.IsAuthenticated, IsStoreOwnerOrManager]

    def get(self, request):
        user = request.user
        store = user.store

        # Platform admins see all non-customer users; store staff see only their store
        if user.role == User.Role.PLATFORM_ADMIN:
            qs = User.objects.filter(role__in=[
                User.Role.STORE_OWNER,
                User.Role.STORE_MANAGER,
            ]).select_related("store").order_by("-date_joined")
        else:
            qs = User.objects.filter(store=store).exclude(
                role=User.Role.CUSTOMER
            ).order_by("-date_joined")

        # Search by name or email
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        data = []
        for u in qs:
            data.append({
                "id": str(u.pk),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": u.role,
                "is_active": u.is_active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            })

        return Response({
            "data": data,
            "meta": {"count": len(data), "next": None, "previous": None},
        })

    def post(self, request):
        user = request.user
        store = user.store

        email = request.data.get("email", "").strip()
        first_name = request.data.get("first_name", "").strip()
        last_name = request.data.get("last_name", "").strip()
        role = request.data.get("role", "cashier")
        password = request.data.get("password", "")

        # Validation
        if not email:
            return Response(
                {"errors": [{"field": "email", "message": "Email is required.", "code": "REQUIRED"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password or len(password) < 6:
            return Response(
                {"errors": [{"field": "password", "message": "Password must be at least 6 characters.", "code": "MIN_LENGTH"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if role not in ("store_manager", "cashier", "waiter"):
            return Response(
                {"errors": [{"field": "role", "message": "Invalid role.", "code": "INVALID"}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check duplicate
        if User.objects.filter(email=email, store=store).exists():
            return Response(
                {"errors": [{"field": "email", "message": "A user with this email already exists in this store.", "code": "DUPLICATE"}]},
                status=status.HTTP_409_CONFLICT,
            )

        # Create user (free — no subscription check for now)
        new_user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            store=store,
            is_active=True,
            password=make_password(password),
        )

        return Response({
            "data": {
                "id": str(new_user.pk),
                "email": new_user.email,
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
                "role": new_user.role,
                "is_active": new_user.is_active,
                "last_login": None,
            }
        }, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    """
    GET   /api/v1/users/{id}/  — get staff detail
    PATCH /api/v1/users/{id}/  — update staff
    DELETE /api/v1/users/{id}/  — deactivate staff
    """

    permission_classes = [permissions.IsAuthenticated, IsStoreOwnerOrManager]

    def get(self, request, user_id):
        user = request.user
        try:
            if user.role == User.Role.PLATFORM_ADMIN:
                target = User.objects.get(pk=user_id)
            else:
                target = User.objects.get(pk=user_id, store=user.store)
        except User.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "User not found."}]},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "data": {
                "id": str(target.pk),
                "email": target.email,
                "first_name": target.first_name,
                "last_name": target.last_name,
                "role": target.role,
                "is_active": target.is_active,
                "last_login": target.last_login.isoformat() if target.last_login else None,
            }
        })

    def patch(self, request, user_id):
        user = request.user
        try:
            if user.role == User.Role.PLATFORM_ADMIN:
                target = User.objects.get(pk=user_id)
            else:
                target = User.objects.get(pk=user_id, store=user.store)
        except User.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "User not found."}]},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update allowed fields
        for field in ("first_name", "last_name", "role", "is_active"):
            if field in request.data:
                setattr(target, field, request.data[field])

        # Password update (optional)
        password = request.data.get("password")
        if password and len(password) >= 6:
            target.password = make_password(password)

        target.save()

        return Response({
            "data": {
                "id": str(target.pk),
                "email": target.email,
                "first_name": target.first_name,
                "last_name": target.last_name,
                "role": target.role,
                "is_active": target.is_active,
                "last_login": target.last_login.isoformat() if target.last_login else None,
            }
        })

    def delete(self, request, user_id):
        user = request.user
        try:
            if user.role == User.Role.PLATFORM_ADMIN:
                target = User.objects.get(pk=user_id)
            else:
                target = User.objects.get(pk=user_id, store=user.store)
        except User.DoesNotExist:
            return Response(
                {"errors": [{"code": "NOT_FOUND", "message": "User not found."}]},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Don't let owner deactivate themselves
        if target.pk == user.pk:
            return Response(
                {"errors": [{"code": "SELF_DEACTIVATE", "message": "Cannot deactivate yourself."}]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Soft deactivate
        target.is_active = False
        target.save(update_fields=["is_active"])

        return Response(status=status.HTTP_204_NO_CONTENT)
