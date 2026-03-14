"""
factory-boy factories for users domain.
"""

import uuid

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda o: f"user-{uuid.uuid4().hex[:8]}@test.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    role = "platform_admin"  # platform admins bypass store ownership checks
