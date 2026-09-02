#!/usr/bin/env python
"""
JOAT Stores - Debug & Test Helper
Usage: python scripts/debug.py [command]
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")


def run_command(cmd, capture_output=True):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture_output, text=True, timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"


def check_python_syntax():
    """Check Python files for syntax errors."""
    print("\n[1/4] Checking Python syntax...")
    errors = []
    for py_file in Path("apps").rglob("*.py"):
        if "migrations" in str(py_file):
            continue
        try:
            with open(py_file, "r") as f:
                compile(f.read(), str(py_file), "exec")
        except SyntaxError as e:
            errors.append(f"  {py_file}: {e}")
    
    if errors:
        print("  FAIL: Syntax errors found")
        for error in errors:
            print(error)
        return False
    print("  OK: No syntax errors")
    return True


def check_imports():
    """Check for import issues."""
    print("\n[2/4] Checking imports...")
    try:
        import django
        django.setup()
        
        # Check key imports
        from apps.store.models import Store
        from apps.product.models import Product
        from apps.order.models import Order
        from apps.payment.models import MpesaTransaction
        from apps.restaurant.models import MenuItem
        from apps.bar.models import Tab
        from apps.contracting.models import Service
        from apps.saas.models import Plan
        from apps.analytics.models import DailyRevenueSummary
        from apps.loyalty.models import LoyaltyAccount
        from apps.users.models import User
        
        print("  OK: All key models import successfully")
        return True
    except Exception as e:
        print(f"  FAIL: Import error - {e}")
        return False


def check_migrations():
    """Check for pending migrations."""
    print("\n[3/4] Checking migrations...")
    code, stdout, stderr = run_command("python manage.py showmigrations --plan")
    if code != 0:
        print(f"  FAIL: {stderr}")
        return False
    
    pending = [line for line in stdout.split("\n") if "[ ]" in line]
    if pending:
        print(f"  WARNING: {len(pending)} pending migrations")
        for migration in pending[:5]:
            print(f"    {migration.strip()}")
        return False
    print("  OK: All migrations applied")
    return True


def check_static_files():
    """Check static files collection."""
    print("\n[4/4] Checking static files...")
    code, stdout, stderr = run_command("python manage.py findstatic --verbosity 0 admin/css/base.css")
    if code == 0:
        print("  OK: Static files accessible")
        return True
    print("  WARNING: Static files may need collection")
    return True


def check_database_connection():
    """Check database connectivity."""
    print("\nChecking database connection...")
    try:
        import django
        django.setup()
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("  OK: PostgreSQL connected")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def check_redis_connection():
    """Check Redis connectivity."""
    print("\nChecking Redis connection...")
    try:
        import django
        django.setup()
        from django.core.cache import cache
        cache.set("debug_test", "ok", 10)
        if cache.get("debug_test") == "ok":
            print("  OK: Redis connected")
            return True
        print("  FAIL: Redis not responding correctly")
        return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def check_celery_workers():
    """Check Celery worker status."""
    print("\nChecking Celery workers...")
    code, stdout, stderr = run_command(
        "docker compose exec django celery -A config.celery_app inspect active"
    )
    if code == 0 and "OK" in stdout:
        print("  OK: Celery workers active")
        return True
    print("  WARNING: Celery workers may not be running")
    return False


def run_linting():
    """Run Python linting."""
    print("\nRunning linting...")
    
    print("  [1/3] flake8...")
    code, stdout, stderr = run_command("flake8 . --count --statistics", capture_output=False)
    if code != 0:
        print("    FAIL: flake8 found issues")
        return False
    
    print("  [2/3] black...")
    code, stdout, stderr = run_command("black --check .")
    if code != 0:
        print("    WARNING: Code needs formatting")
    
    print("  [3/3] isort...")
    code, stdout, stderr = run_command("isort --check-only .")
    if code != 0:
        print("    WARNING: Imports need sorting")
    
    print("  OK: Linting complete")
    return True


def run_tests_fast():
    """Run a quick subset of tests."""
    print("\nRunning fast tests...")
    
    # Run tests that don't require database
    test_files = [
        "apps/store/tests/test_models.py::TestStoreCreation::test_store_str",
    ]
    
    for test_file in test_files:
        code, stdout, stderr = run_command(f"python -m pytest {test_file} -v --tb=short")
        if code == 0:
            print(f"  PASS: {test_file}")
        else:
            print(f"  FAIL: {test_file}")
    
    return True


def show_model_summary():
    """Show summary of all models."""
    print("\nModel Summary")
    print("=" * 60)
    
    try:
        import django
        django.setup()
        
        from django.apps import apps
        models = apps.get_models()
        
        by_app = {}
        for model in models:
            app_label = model._meta.app_label
            if app_label not in by_app:
                by_app[app_label] = []
            by_app[app_label].append(model.__name__)
        
        for app, model_list in sorted(by_app.items()):
            print(f"\n{app.upper()} ({len(model_list)} models)")
            for model in sorted(model_list):
                print(f"  - {model}")
        
        print(f"\nTotal: {len(models)} models")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def show_url_patterns():
    """Show URL patterns."""
    print("\nURL Patterns")
    print("=" * 60)
    
    try:
        import django
        django.setup()
        from django.urls import get_resolver
        
        resolver = get_resolver()
        urls = []
        
        def collect_urls(patterns, prefix=""):
            for pattern in patterns:
                if hasattr(pattern, "url_patterns"):
                    collect_urls(pattern.url_patterns, prefix + str(pattern.pattern))
                else:
                    urls.append(prefix + str(pattern.pattern))
        
        collect_urls(resolver.url_patterns)
        
        for url in sorted(urls):
            print(f"  {url}")
        
        print(f"\nTotal: {len(urls)} URL patterns")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("\nJOAT Stores - Debug Helper")
        print("=" * 60)
        print("\nUsage: python scripts/debug.py [command]")
        print("\nCommands:")
        print("  check       - Run all checks")
        print("  syntax      - Check Python syntax")
        print("  imports     - Check imports")
        print("  migrations  - Check migrations")
        print("  database    - Check database connection")
        print("  redis       - Check Redis connection")
        print("  celery      - Check Celery workers")
        print("  lint        - Run linting")
        print("  test        - Run fast tests")
        print("  models      - Show model summary")
        print("  urls        - Show URL patterns")
        print("  full        - Run full health check")
        return
    
    command = sys.argv[1]
    
    if command == "check":
        check_python_syntax()
        check_imports()
        check_migrations()
        check_static_files()
    elif command == "syntax":
        check_python_syntax()
    elif command == "imports":
        check_imports()
    elif command == "migrations":
        check_migrations()
    elif command == "database":
        check_database_connection()
    elif command == "redis":
        check_redis_connection()
    elif command == "celery":
        check_celery_workers()
    elif command == "lint":
        run_linting()
    elif command == "test":
        run_tests_fast()
    elif command == "models":
        show_model_summary()
    elif command == "urls":
        show_url_patterns()
    elif command == "full":
        print("\n" + "=" * 60)
        print("FULL HEALTH CHECK")
        print("=" * 60)
        
        results = {
            "Python Syntax": check_python_syntax(),
            "Imports": check_imports(),
            "Migrations": check_migrations(),
            "Database": check_database_connection(),
            "Redis": check_redis_connection(),
            "Linting": run_linting(),
        }
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for check, passed in results.items():
            status = "PASS" if passed else "FAIL"
            print(f"  {check}: {status}")
        
        all_passed = all(results.values())
        print(f"\nOverall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    else:
        print(f"Unknown command: {command}")
        print("Run 'python scripts/debug.py' for help")


if __name__ == "__main__":
    main()
