#!/usr/bin/env python
"""
Quick test script - runs without database
Usage: python scripts/quick_test.py
"""

import os
import sys
import ast
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def check_syntax():
    """Check all Python files for syntax errors."""
    print("\n[1/3] Checking Python syntax...")
    errors = []
    files_checked = 0
    
    for py_file in Path("backend/apps").rglob("*.py"):
        if "migrations" in str(py_file) or "__pycache__" in str(py_file):
            continue
        
        files_checked += 1
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source, filename=str(py_file))
        except SyntaxError as e:
            errors.append(f"  {py_file}: line {e.lineno} - {e.msg}")
    
    if errors:
        print(f"  FAIL: {len(errors)} syntax errors found in {files_checked} files")
        for error in errors:
            print(error)
        return False
    
    print(f"  OK: {files_checked} files checked, no syntax errors")
    return True


def check_imports():
    """Check that key modules can be imported."""
    print("\n[2/3] Checking imports...")
    
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.local"
    
    try:
        import django
        django.setup()
        
        modules = [
            ("apps.store.models", "Store"),
            ("apps.product.models", "Product"),
            ("apps.order.models", "Order"),
            ("apps.payment.models", "MpesaTransaction"),
            ("apps.restaurant.models", "MenuItem"),
            ("apps.bar.models", "Tab"),
            ("apps.contracting.models", "Service"),
            ("apps.saas.models", "Plan"),
            ("apps.analytics.models", "DailyRevenueSummary"),
            ("apps.loyalty.models", "LoyaltyAccount"),
            ("apps.users.models", "User"),
            ("core.models", "TenantModel"),
        ]
        
        for module_name, class_name in modules:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
                print(f"  OK: {module_name}.{class_name}")
            except Exception as e:
                print(f"  FAIL: {module_name}.{class_name} - {e}")
                return False
        
        print(f"  OK: All {len(modules)} key modules imported successfully")
        return True
        
    except Exception as e:
        print(f"  FAIL: Django setup failed - {e}")
        return False


def check_model_fields():
    """Check that key models have expected fields."""
    print("\n[3/3] Checking model fields...")
    
    try:
        import django
        django.setup()
        
        from apps.store.models import Store
        from apps.product.models import Product, Variant
        from apps.order.models import Order
        from apps.payment.models import MpesaTransaction
        
        checks = [
            (Store, ["name", "slug", "domain", "tenant_type", "status", "currency"]),
            (Product, ["name", "description", "is_available"]),
            (Variant, ["price", "inventory_count", "sku"]),
            (Order, ["customer_phone", "total_amount", "status", "items_snapshot"]),
            (MpesaTransaction, ["phone", "amount", "status", "mpesa_receipt_number"]),
        ]
        
        for model, expected_fields in checks:
            model_fields = [f.name for f in model._meta.get_fields()]
            missing = [f for f in expected_fields if f not in model_fields]
            
            if missing:
                print(f"  FAIL: {model.__name__} missing fields: {missing}")
                return False
            print(f"  OK: {model.__name__} has all expected fields")
        
        print(f"  OK: All model field checks passed")
        return True
        
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def main():
    """Run all quick tests."""
    print("=" * 60)
    print("JOAT STORES - QUICK TEST")
    print("=" * 60)
    
    results = {
        "Syntax": check_syntax(),
        "Imports": check_imports(),
        "Model Fields": check_model_fields(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
