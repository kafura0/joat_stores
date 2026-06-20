"""
Root pytest conftest.

Convention: Tests requiring DB access must opt in with @pytest.mark.django_db.
This keeps unit tests (serializers, validators, utility functions) fast
by not spinning up a test database for every test.
"""
